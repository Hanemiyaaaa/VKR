FROM apache/airflow:2.8.1-python3.11

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    openjdk-17-jre-headless \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Spark
ENV SPARK_VERSION=3.4.3
ENV HADOOP_VERSION=3
RUN wget -q https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz && \
    tar -xzf spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz -C /opt && \
    mv /opt/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION} /opt/spark && \
    rm spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz

ENV SPARK_HOME=/opt/spark
ENV PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
ENV PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.7-src.zip:$PYTHONPATH

USER airflow
RUN pip install --no-cache-dir \
    apache-airflow \
    pyspark \
    psycopg2-binary \
    pandas

COPY ./dags /opt/airflow/dags
COPY ./scripts /opt/airflow/scripts