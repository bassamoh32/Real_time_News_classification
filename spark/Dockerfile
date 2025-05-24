FROM bitnami/spark:latest

WORKDIR /app

COPY ./cassandra /app/cassandra
COPY ./spark/consumer.py .

RUN pip install --no-cache-dir --upgrade -r requirements.txt

ENV PYTHONPATH=/app

CMD ["spark-submit", \
   "--master", "spark://spark-master:7077", \
   "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.1,com.datastax.spark:spark-cassandra-connector_2.12:3.2.0", \
   "--conf", "spark.cassandra.connection.host=cassandra", \
   "--conf", "spark.cassandra.connection.port=9042", \
   "--conf", "spark.cassandra.auth.username=admin", \
   "--conf", "spark.cassandra.auth.password=admin", \
   "/app/consumer.py"]