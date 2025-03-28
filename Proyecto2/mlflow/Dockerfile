FROM python:3.8
WORKDIR /app
RUN pip install mlflow pymysql mysql-connector-python boto3 cryptography
CMD ["mlflow", "server", "--backend-store-uri", "mysql+pymysql://airflow:airflow@mysql:3306/mlflow", "--default-artifact-root", "s3://mlflows3/artifacts", "--host", "0.0.0.0", "--serve-artifacts"]
