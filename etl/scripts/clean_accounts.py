#!/usr/bin/env python3
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, trim, when, lit, to_json, struct, current_timestamp
from pyspark.sql.types import StringType

def clean_accounts(input_path, file_id, target_table, db_url, db_user, db_password):
    spark = SparkSession.builder.appName("CleanAccounts").getOrCreate()
    df = spark.read.option("header", "true").csv(input_path)
    df = df.withColumn("_file_id", lit(int(file_id)))
    
    mandatory = ["account_number", "name"]
    valid_condition = lit(True)
    for field in mandatory:
        if field in df.columns:
            cond = col(field).isNotNull() & (trim(col(field)) != lit(""))
            valid_condition = valid_condition & cond
        else:
            valid_condition = valid_condition & lit(False)
    
    if "account_type" in df.columns:
        valid_types = ["asset", "settlement", "deposit", "loan", "cash", "other"]
        cond = col("account_type").isin(valid_types) | col("account_type").isNull()
        valid_condition = valid_condition & cond
    if "currency" in df.columns:
        cond = col("currency").rlike("^[A-Z]{3}$") | col("currency").isNull()
        valid_condition = valid_condition & cond
    
    df_valid = df.filter(valid_condition)
    df_invalid = df.filter(~valid_condition)
    valid_count = df_valid.count()
    
    # Запись валидных строк в staging
    if valid_count > 0:
        df_valid = df_valid.withColumn("account_number", trim(col("account_number")))
        df_valid = df_valid.withColumn("name", trim(col("name")))
        if "account_type" in df_valid.columns:
            df_valid = df_valid.withColumn("account_type", when(col("account_type").isNull(), "asset").otherwise(trim(col("account_type"))))
        else:
            df_valid = df_valid.withColumn("account_type", lit("asset"))
        if "currency" in df_valid.columns:
            df_valid = df_valid.withColumn("currency", when(col("currency").isNull(), "RUB").otherwise(trim(col("currency"))))
        else:
            df_valid = df_valid.withColumn("currency", lit("RUB"))
        
        staging_table = f"staging_{target_table}"
        cols_to_save = ["account_number", "name", "account_type", "currency"]
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
    
    # Запись невалидных строк в etl_errors
    if df_invalid.count() > 0:
        df_errors = df_invalid.withColumn("row_json", to_json(struct([col(c) for c in df_invalid.columns]))) \
            .select(
                col("_file_id").alias("file_id"),
                lit(target_table).alias("data_type"),
                col("row_json").alias("row_data"),
                lit("Missing mandatory fields (account_number, name) or invalid account_type/currency").alias("error_reason"),
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
        print(f"Invalid rows: {df_invalid.count()} written to etl_errors")
    
    spark.stop()
    return valid_count

if __name__ == "__main__":
    if len(sys.argv) < 7:
        print("Usage: clean_accounts.py <input_path> <file_id> <target_table> <db_url> <db_user> <db_password>")
        sys.exit(1)
    input_path = sys.argv[1]
    file_id = sys.argv[2]
    target_table = sys.argv[3]
    db_url = sys.argv[4]
    db_user = sys.argv[5]
    db_password = sys.argv[6]
    clean_accounts(input_path, file_id, target_table, db_url, db_user, db_password)