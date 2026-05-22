#!/usr/bin/env python3
"""
Ожидаемые колонки в CSV: account, balance, date
Связан с таблицей accounts через account_number.
Валидные строки записываются в staging_initial_balances с полями account_id, balance, date, file_id, version.
Невалидные (не найден счёт, неверный формат даты, пустые значения) логируются в etl_errors.
"""

import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, trim, when, to_date, lit, to_json, struct, current_timestamp
from pyspark.sql.types import DecimalType

def clean_initial_balances(input_path, file_id, target_table, db_url, db_user, db_password):
    spark = SparkSession.builder.appName("CleanInitialBalances").getOrCreate()

    df = spark.read.option("header", "true").csv(input_path)
    df = df.withColumn("_file_id", lit(int(file_id)))

    mandatory = ["account", "balance", "date"]
    valid_condition = lit(True)

    for field in mandatory:
        if field in df.columns:
            cond = col(field).isNotNull() & (trim(col(field)) != lit(""))
            valid_condition = valid_condition & cond
        else:
            valid_condition = valid_condition & lit(False)

    if "date" in df.columns:
        valid_condition = valid_condition & to_date(col("date"), "yyyy-MM-dd").isNotNull()
    if "balance" in df.columns:
        valid_condition = valid_condition & col("balance").rlike("^-?[0-9]+\.?[0-9]*$")

    df_valid_csv = df.filter(valid_condition)
    df_invalid_csv = df.filter(~valid_condition)

    # Если есть валидные по формату строки, загружаем accounts для сопоставления
    valid_count = 0
    if df_valid_csv.count() > 0:
        accounts_df = spark.read \
            .format("jdbc") \
            .option("url", db_url) \
            .option("dbtable", "accounts") \
            .option("user", db_user) \
            .option("password", db_password) \
            .option("driver", "org.postgresql.Driver") \
            .load() \
            .select(col("account_number").alias("acc_number"), col("id").alias("account_id"))

        # Присоединяем account_id
        df_with_account = df_valid_csv.join(accounts_df, df_valid_csv["account"] == accounts_df["acc_number"], "left")
        df_final_valid = df_with_account.filter(col("account_id").isNotNull())
        df_invalid_account = df_with_account.filter(col("account_id").isNull())

        if df_final_valid.count() > 0:
            df_final_valid = df_final_valid.withColumn("balance", col("balance").cast(DecimalType(15,2)))
            df_final_valid = df_final_valid.withColumn("date", to_date(col("date"), "yyyy-MM-dd"))
            df_final_valid = df_final_valid.withColumn("file_id", lit(int(file_id)))
            df_final_valid = df_final_valid.withColumn("version", lit("original"))
            # Убираем лишние колонки, оставляем только нужные для staging
            df_final_valid = df_final_valid.select("account_id", "balance", "date", "file_id", "version")
            staging_table = f"staging_{target_table}"
            df_final_valid.write.mode("overwrite") \
                .format("jdbc") \
                .option("url", db_url) \
                .option("dbtable", staging_table) \
                .option("user", db_user) \
                .option("password", db_password) \
                .option("driver", "org.postgresql.Driver") \
                .save()
            valid_count = df_final_valid.count()
            print(f"Valid rows: {valid_count} written to {staging_table}")

        # Логируем невалидные строки (неверный формат CSV)
        if df_invalid_csv.count() > 0:
            df_errors = df_invalid_csv.withColumn("row_json", to_json(struct([col(c) for c in df_invalid_csv.columns]))) \
                .select(
                    col("_file_id").alias("file_id"),
                    lit(target_table).alias("data_type"),
                    col("row_json").alias("row_data"),
                    lit("Missing mandatory fields or invalid date/number format").alias("error_reason"),
                    current_timestamp().alias("timestamp")
                )
            df_errors.write.mode("append") \
                .format("jdbc") \
                .option("url", db_url) \
                .option("dbtable", "etl_errors") \
                .option("user", db_user) \
                .option("password", db_password) \
                .option("driver", "org.postgresql.Driver") \
                .save()
            print(f"CSV invalid rows: {df_invalid_csv.count()} written to etl_errors")

        # Логируем строки с неизвестным счётом
        if df_invalid_account.count() > 0:
            df_errors_acc = df_invalid_account.withColumn("row_json", to_json(struct([col(c) for c in df_invalid_account.columns]))) \
                .select(
                    col("_file_id").alias("file_id"),
                    lit(target_table).alias("data_type"),
                    col("row_json").alias("row_data"),
                    lit("Account number not found in accounts table").alias("error_reason"),
                    current_timestamp().alias("timestamp")
                )
            df_errors_acc.write.mode("append") \
                .format("jdbc") \
                .option("url", db_url) \
                .option("dbtable", "etl_errors") \
                .option("user", db_user) \
                .option("password", db_password) \
                .option("driver", "org.postgresql.Driver") \
                .save()
            print(f"Invalid account rows: {df_invalid_account.count()} written to etl_errors")
    else:
        # Все строки невалидны по формату CSV
        if df_invalid_csv.count() > 0:
            df_errors = df_invalid_csv.withColumn("row_json", to_json(struct([col(c) for c in df_invalid_csv.columns]))) \
                .select(
                    col("_file_id").alias("file_id"),
                    lit(target_table).alias("data_type"),
                    col("row_json").alias("row_data"),
                    lit("Missing mandatory fields or invalid date/number format").alias("error_reason"),
                    current_timestamp().alias("timestamp")
                )
            df_errors.write.mode("append") \
                .format("jdbc") \
                .option("url", db_url) \
                .option("dbtable", "etl_errors") \
                .option("user", db_user) \
                .option("password", db_password) \
                .option("driver", "org.postgresql.Driver") \
                .save()
            print(f"All rows invalid: {df_invalid_csv.count()} written to etl_errors")

    spark.stop()
    return valid_count

if __name__ == "__main__":
    if len(sys.argv) < 7:
        print("Usage: clean_initial_balances.py <input_path> <file_id> <target_table> <db_url> <db_user> <db_password>")
        sys.exit(1)
    input_path = sys.argv[1]
    file_id = sys.argv[2]
    target_table = sys.argv[3]
    db_url = sys.argv[4]
    db_user = sys.argv[5]
    db_password = sys.argv[6]
    clean_initial_balances(input_path, file_id, target_table, db_url, db_user, db_password)