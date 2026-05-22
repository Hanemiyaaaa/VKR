#!/usr/bin/env python3
"""
Spark-скрипт для очистки данных о депозитах (deposits).
Ожидаемые колонки в CSV: deposit_account_number, amount, interest_rate, start_date, end_date, term_type, currency
"""

import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, trim, when, to_date, lit, to_json, struct, current_timestamp
from pyspark.sql.types import DecimalType, StringType

def clean_deposits(input_path, file_id, target_table, db_url, db_user, db_password):
    spark = SparkSession.builder.appName("CleanDeposits").getOrCreate()
    df = spark.read.option("header", "true").csv(input_path)
    df = df.withColumn("_file_id", lit(int(file_id)))

    mandatory = ["deposit_account_number", "amount", "interest_rate", "start_date", "end_date", "term_type"]
    valid_condition = lit(True)

    for field in mandatory:
        if field in df.columns:
            cond = col(field).isNotNull() & (trim(col(field)) != lit(""))
            valid_condition = valid_condition & cond
        else:
            valid_condition = valid_condition & lit(False)

    if "start_date" in df.columns:
        valid_condition = valid_condition & to_date(col("start_date"), "yyyy-MM-dd").isNotNull()
    if "end_date" in df.columns:
        valid_condition = valid_condition & to_date(col("end_date"), "yyyy-MM-dd").isNotNull()
        valid_condition = valid_condition & (to_date(col("end_date"), "yyyy-MM-dd") >= to_date(col("start_date"), "yyyy-MM-dd"))

    if "amount" in df.columns:
        valid_condition = valid_condition & col("amount").rlike("^[0-9]+\.?[0-9]*$")
    if "interest_rate" in df.columns:
        valid_condition = valid_condition & col("interest_rate").rlike("^[0-9]+\.?[0-9]*$")

    if "term_type" in df.columns:
        valid_condition = valid_condition & col("term_type").isin(["on_demand", "30_days", "1_year"])

    df_valid = df.filter(valid_condition)
    df_invalid = df.filter(~valid_condition)

    valid_count = df_valid.count()
    invalid_count = df_invalid.count()

    if valid_count > 0:
        df_valid = df_valid.withColumn("amount", col("amount").cast(DecimalType(15,2)))
        df_valid = df_valid.withColumn("interest_rate", col("interest_rate").cast(DecimalType(5,2)))
        df_valid = df_valid.withColumn("start_date", to_date(col("start_date"), "yyyy-MM-dd"))
        df_valid = df_valid.withColumn("end_date", to_date(col("end_date"), "yyyy-MM-dd"))
        for field in ["deposit_account_number", "term_type", "currency"]:
            if field in df_valid.columns:
                df_valid = df_valid.withColumn(field, trim(col(field)))
        if "currency" in df_valid.columns:
            df_valid = df_valid.withColumn("currency", when(col("currency").isNull(), "RUB").otherwise(col("currency")))
        else:
            df_valid = df_valid.withColumn("currency", lit("RUB"))

        # Добавляем служебные колонки
        df_valid = df_valid.withColumn("file_id", lit(int(file_id)))
        df_valid = df_valid.withColumn("version", lit("original"))

        staging_table = f"staging_{target_table}"
        cols_to_save = [c for c in df_valid.columns if c != "_file_id"]
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
        df_errors = df_invalid.withColumn("row_json", to_json(struct([col(c) for c in df_invalid.columns]))) \
            .select(
                col("_file_id").alias("file_id"),
                lit(target_table).alias("data_type"),
                col("row_json").alias("row_data"),
                lit("Missing mandatory fields or invalid date/number/term_type").alias("error_reason"),
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
        print("Usage: clean_deposits.py <input_path> <file_id> <target_table> <db_url> <db_user> <db_password>")
        sys.exit(1)
    input_path = sys.argv[1]
    file_id = sys.argv[2]
    target_table = sys.argv[3]
    db_url = sys.argv[4]
    db_user = sys.argv[5]
    db_password = sys.argv[6]
    clean_deposits(input_path, file_id, target_table, db_url, db_user, db_password)