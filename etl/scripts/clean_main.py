#!/usr/bin/env python3
"""
Spark-скрипт для очистки основных данных (data_table).
Ожидаемые колонки в CSV: account_id, client_type, product_type, balance, currency, risk_flag
"""

import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, trim, when, lit, to_json, struct, current_timestamp
from pyspark.sql.types import DecimalType
from pyspark.sql.functions import upper

def clean_main(input_path, file_id, target_table, db_url, db_user, db_password):
    spark = SparkSession.builder.appName("CleanMain").getOrCreate()
    df = spark.read.option("header", "true").csv(input_path)
    df = df.withColumn("_file_id", lit(int(file_id)))

    mandatory = ["account_id", "client_type", "product_type", "balance", "currency", "risk_flag"]
    valid_condition = lit(True)

    for field in mandatory:
        if field in df.columns:
            cond = col(field).isNotNull() & (trim(col(field)) != lit(""))
            valid_condition = valid_condition & cond
        else:
            valid_condition = valid_condition & lit(False)

    # Проверка balance: должно быть числом (может быть отрицательным)
    if "balance" in df.columns:
        valid_condition = valid_condition & col("balance").rlike("^-?[0-9]+\.?[0-9]*$")

    # currency – три заглавные латинские буквы
    if "currency" in df.columns:
        valid_currencies = ["RUB", "USD", "EUR", "GBP", "CNY", "JPY"]
        valid_condition = valid_condition & col("currency").isin(valid_currencies)

    # risk_flag – допустимые значения
    if "risk_flag" in df.columns:
        valid_condition = valid_condition & col("risk_flag").isin(["LOW", "MEDIUM", "HIGH"])

    df_valid = df.filter(valid_condition)
    df_invalid = df.filter(~valid_condition)

    valid_count = df_valid.count()
    invalid_count = df_invalid.count()

    if valid_count > 0:
        # Приведение типов
        df_valid = df_valid.withColumn("balance", col("balance").cast(DecimalType(15,2)))
        # Очистка строковых полей
        for field in mandatory:
            if field in df_valid.columns:
                df_valid = df_valid.withColumn(field, trim(col(field)))
        # Заполнение значений по умолчанию (если NULL, хотя они уже отфильтрованы)
        df_valid = df_valid.withColumn("currency", when(col("currency").isNull(), "RUB").otherwise(col("currency")))
        df_valid = df_valid.withColumn("risk_flag", when(col("risk_flag").isNull(), "LOW").otherwise(col("risk_flag")))
        df_valid = df_valid.withColumn("file_id", lit(int(file_id)))
        df_valid = df_valid.withColumn("version", lit("original"))
        df_valid = df_valid.withColumn("currency", upper(col("currency")))

        staging_table = f"staging_{target_table}"
        cols_to_save = ["account_id", "client_type", "product_type", "balance", "currency", "risk_flag", "file_id", "version"]
        # Запись в staging (перезапись)
        df_valid.select(*cols_to_save).write.mode("overwrite") \
            .format("jdbc") \
            .option("url", db_url) \
            .option("dbtable", staging_table) \
            .option("user", db_user) \
            .option("password", db_password) \
            .option("driver", "org.postgresql.Driver") \
            .save()
        print(f"Valid rows: {valid_count} written to {staging_table}")
    else:
        print("No valid rows found")

    if invalid_count > 0:
        # Логирование невалидных строк
        df_errors = df_invalid.withColumn("row_json", to_json(struct([col(c) for c in df_invalid.columns]))) \
            .select(
                col("_file_id").alias("file_id"),
                lit(target_table).alias("data_type"),
                col("row_json").alias("row_data"),
                lit("Missing mandatory fields or invalid balance/currency/risk_flag").alias("error_reason"),
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
        print(f"Invalid rows: {invalid_count} written to etl_errors")

    spark.stop()
    return valid_count

if __name__ == "__main__":
    if len(sys.argv) < 7:
        print("Usage: clean_main.py <input_path> <file_id> <target_table> <db_url> <db_user> <db_password>")
        sys.exit(1)
    input_path = sys.argv[1]
    file_id = sys.argv[2]
    target_table = sys.argv[3]
    db_url = sys.argv[4]
    db_user = sys.argv[5]
    db_password = sys.argv[6]
    clean_main(input_path, file_id, target_table, db_url, db_user, db_password)