"""
DAG для ETL-обработки загруженных файлов с использованием Spark.
Ожидает, что в БД есть таблицы:
- file_registry, etl_logs, staging_<data_type>, а также основные таблицы (accounts, loans, ...)
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.sql import SqlSensor
from datetime import datetime, timedelta
import subprocess
import psycopg2
from psycopg2.extras import RealDictCursor

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 5, 16),
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}

dag = DAG(
    'data_quality_dag',
    default_args=default_args,
    description='Очистка загруженных файлов с помощью Spark и слияние в основные таблицы',
    schedule_interval=timedelta(minutes=5),
    catchup=False,
)

check_pending = SqlSensor(
    task_id='check_pending_files',
    conn_id='postgres_default',
    sql="SELECT COUNT(*) FROM file_registry WHERE status = 'pending'",
    poke_interval=30,
    timeout=600,
    mode='poke',
    dag=dag,
)

def process_one_file(**context):
    """Извлекает запись со статусом pending, запускает Spark-очистку в staging."""
    conn = psycopg2.connect(
        host='db',
        database='mvp_db',
        user='postgres',
        password='loko1908'
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)
    row = None
    try:
        cur.execute("""
            SELECT id, file_id, file_path, data_type
            FROM file_registry
            WHERE status = 'pending'
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        """)
        row = cur.fetchone()
        if not row:
            return

        registry_id = row['id']
        file_id = row['file_id']
        file_path = row['file_path']
        data_type = row['data_type']

        cur.execute("UPDATE file_registry SET status = 'processing' WHERE id = %s", (registry_id,))
        cur.execute("""
            INSERT INTO etl_logs (file_id, data_type, status, started_at)
            VALUES (%s, %s, 'started', %s)
        """, (file_id, data_type, datetime.utcnow()))
        conn.commit()

        script_map = {
            'accounts': 'clean_accounts.py',
            'loans': 'clean_loans.py',
            'deposits': 'clean_deposits.py',
            'bonds': 'clean_bonds.py',
            'exchange_rates': 'clean_exchange_rates.py',
            'capital': 'clean_capital.py',
            'transactions': 'clean_transactions.py',
            'main': 'clean_main.py',
            'initial_balances': 'clean_initial_balances.py',
        }
        script = script_map.get(data_type)
        if not script:
            raise ValueError(f"Неизвестный тип данных: {data_type}")

        db_url = "jdbc:postgresql://db:5432/mvp_db"
        cmd = [
            "spark-submit",
            f"/opt/airflow/scripts/{script}",
            file_path,
            str(file_id),
            data_type,
            db_url,
            "postgres",
            "loko1908"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            cur.execute("UPDATE file_registry SET status = 'staged' WHERE id = %s", (registry_id,))
            cur.execute("""
                UPDATE etl_logs SET status = 'staged', finished_at = %s
                WHERE file_id = %s AND status = 'started'
            """, (datetime.utcnow(), file_id))
        else:
            error_msg = result.stderr[:2000]
            cur.execute("UPDATE file_registry SET status = 'error' WHERE id = %s", (registry_id,))
            cur.execute("""
                UPDATE etl_logs SET status = 'failed', errors = %s, finished_at = %s
                WHERE file_id = %s AND status = 'started'
            """, (error_msg, datetime.utcnow(), file_id))
        conn.commit()

        context['ti'].xcom_push(key='processed_file', value={
            'registry_id': registry_id,
            'file_id': file_id,
            'data_type': data_type,
            'status': 'staged' if result.returncode == 0 else 'error'
        })
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)

    except Exception as e:
        conn.rollback()
        if row:
            cur.execute("""
                INSERT INTO etl_logs (file_id, data_type, status, errors, finished_at)
                VALUES (%s, %s, 'failed', %s, %s)
            """, (row['file_id'], row['data_type'], str(e)[:2000], datetime.utcnow()))
            cur.execute("UPDATE file_registry SET status = 'error' WHERE id = %s", (row['id'],))
            conn.commit()
        raise
    finally:
        cur.close()
        conn.close()

def merge_staging_to_final_sql():
    """Выполняет слияние, читая SQL из файла merge_staging_to_final.sql"""
    conn = psycopg2.connect(
        host='db',
        database='mvp_db',
        user='postgres',
        password='loko1908'
    )
    cur = conn.cursor()
    try:
        with open('/opt/airflow/scripts/merge_staging_to_final.sql', 'r') as f:
            sql = f.read()
        cur.execute(sql)
        conn.commit()
        print("Merge completed successfully via SQL file")
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

process_task = PythonOperator(
    task_id='process_one_file',
    python_callable=process_one_file,
    provide_context=True,
    dag=dag,
)

merge_task = PythonOperator(
    task_id='merge_staging_to_final',
    python_callable=merge_staging_to_final_sql,
    dag=dag,
)

check_pending >> process_task >> merge_task