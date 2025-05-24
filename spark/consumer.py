import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_timestamp, to_date, lit
from pyspark.sql.types import StructType, StringType, TimestampType
import yaml

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from cassandra.cassandra_manager import CassandraManager

def load_config(config_file):
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'configuration',
        config_file
    )
    with open(config_path) as f:
        return yaml.safe_load(f)

kafka_config = load_config('kafka.yml')
cassandra_config = load_config('cassandra.yml')

cassandra = CassandraManager(
    host=cassandra_config['HOST'],
    keyspace=cassandra_config['KEYSPACE'],
    table=cassandra_config['TABLE'],
    username=cassandra_config['USERNAME'],
    password=cassandra_config['PASSWORD']
)
cassandra.connect()

def process_batch(df, batch_id):
    if df.head(1):
        print(f"Processing batch {batch_id} with {df.count()} records")
        try:
            processed_df = df.withColumnRenamed("publishedAt", "post_time") \
                             .withColumn("post_time", to_timestamp(col("post_time"))) \
                             .withColumn("post_date", to_date(col("post_time"))) \
                             .withColumn("new_id", lit(None).cast(StringType())) \
                             .withColumn("prediction", lit(None).cast(StringType()))

            final_df = processed_df.select(
                "new_id", "title", "description", "url",
                "post_date", "post_time", "source", "category", "prediction"
            )

            final_df.write \
                .format("org.apache.spark.sql.cassandra") \
                .options(
                    table=cassandra_config['TABLE'],
                    keyspace=cassandra_config['KEYSPACE']
                ) \
                .mode("append") \
                .save()

            print(f"Successfully wrote batch {batch_id} to Cassandra")
        except Exception as e:
            print(f"Error writing to Cassandra: {str(e)}")
    else:
        print(f"Batch {batch_id} is empty, skipping write")

def start_spark():
    spark = SparkSession.builder \
        .appName("NewsStreamProcessor") \
        .config("spark.jars.packages", ",".join([
            "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.1",
            "com.datastax.spark:spark-cassandra-connector_2.12:3.3.0"
        ])) \
        .config("spark.cassandra.connection.host", cassandra_config['HOST']) \
        .config("spark.cassandra.auth.username", cassandra_config.get('USERNAME', '')) \
        .config("spark.cassandra.auth.password", cassandra_config.get('PASSWORD', '')) \
        .config("spark.sql.streaming.checkpointLocation", "/tmp/checkpoints/news") \
        .getOrCreate()

    schema = StructType() \
        .add("title", StringType()) \
        .add("description", StringType()) \
        .add("url", StringType()) \
        .add("publishedAt", StringType()) \
        .add("source", StringType()) \
        .add("category", StringType())

    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_config['BROKER']) \
        .option("subscribe", kafka_config['TOPIC']) \
        .option("startingOffsets", "latest") \
        .load()

    json_df = df.selectExpr("CAST(value AS STRING) as json_str") \
        .select(from_json(col("json_str"), schema).alias("data")) \
        .select("data.*")

    query = json_df.writeStream \
        .foreachBatch(process_batch) \
        .start()

    print("Spark streaming started. Waiting for data from Kafka...")
    query.awaitTermination()

if __name__ == "__main__":
    try:
        start_spark()
    except Exception as e:
        print(f"Application error: {str(e)}")
    finally:
        if 'cassandra' in locals():
            cassandra.close()
