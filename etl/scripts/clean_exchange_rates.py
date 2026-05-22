#!/usr/bin/env python3
"""
Ожидаемые колонки в CSV: currency, rate_to_rub, date
"""

import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, trim, when, to_date, lit, to_json, struct, current_timestamp
from pyspark.sql.types import DecimalType, StringType

def clean_exchange_rates(input_path, file_id, target_table, db_url, db_user, db_password):
    spark = SparkSession.builder.appName("CleanExchangeRates").getOrCreate()
    df = spark.read.option("header", "true").csv(input_path)
    df = df.withColumn("_file_id", lit(int(file_id)))

    mandatory = ["currency", "rate_to_rub", "date"]
    valid_condition = lit(True)

    for field in mandatory:
        if field in df.columns:
            cond = col(field).isNotNull() & (trim(col(field)) != lit(""))
            valid_condition = valid_condition & cond
        else:
            valid_condition = valid_condition & lit(False)

    if "date" in df.columns:
        valid_condition = valid_condition & to_date(col("date"), "yyyy-MM-dd").isNotNull()

    if "rate_to_rub" in df.columns:
        valid_condition = valid_condition & col("rate_to_rub").rlike("^[0-9]+\.?[0-9]*$")

    if "currency" in df.columns:
        valid_condition = valid_condition & col("currency").rlike("^[A-Za-z]{3}$")

    df_valid = df.filter(valid_condition)
    df_invalid = df.filter(~valid_condition)

    valid_count = df_valid.count()
    invalid_count = df_invalid.count()

    if valid_count > 0:
        df_valid = df_valid.withColumn("rate_to_rub", col("rate_to_rub").cast(DecimalType(12,4)))
        df_valid = df_valid.withColumn("date", to_date(col("date"), "yyyy-MM-dd"))
        if "currency" in df_valid.columns:
            df_valid = df_valid.withColumn("currency", trim(col("currency")))

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
                lit("Missing mandatory fields (currency, rate_to_rub, date) or invalid currency code/date/number format").alias("error_reason"),
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
        print("Usage: clean_exchange_rates.py <input_path> <file_id> <target_table> <db_url> <db_user> <db_password>")
        sys.exit(1)
    input_path = sys.argv[1]
    file_id = sys.argv[2]
    target_table = sys.argv[3]
    db_url = sys.argv[4]
    db_user = sys.argv[5]
    db_password = sys.argv[6]
    clean_exchange_rates(input_path, file_id, target_table, db_url, db_user, db_password)