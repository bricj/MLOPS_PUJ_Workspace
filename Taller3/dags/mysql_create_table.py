from airflow import DAG
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.operators.python import PythonOperator
from datetime import datetime
import pandas as pd
import os

# Ruta del archivo en el volumen compartido
FILE_PATH = "/opt/airflow/data/datos.csv"

# Función para leer el archivo y cargarlo en MySQL
def load_csv_to_mysql():
    mysql_hook = MySqlHook(mysql_conn_id="mysql_airflow_conn")  # Debes definir esta conexión en Airflow
    engine = mysql_hook.get_sqlalchemy_engine()

    # Leer el archivo CSV
    df = pd.read_csv(FILE_PATH)

    # Crear la tabla en MySQL
    create_table_query = """
    CREATE TABLE IF NOT EXISTS personas (
        id INT PRIMARY KEY,
        nombre VARCHAR(100),
        edad INT
    )
    """
    
    with engine.begin() as connection:
        connection.execute(create_table_query)
        df.to_sql(name="personas", con=connection, if_exists="replace", index=False)

# Definir el DAG
default_args = {
    "owner": "airflow",
    "start_date": datetime(2024, 3, 5),
    "retries": 1,
}

with DAG(
    dag_id="crear_tabla_mysql",
    default_args=default_args,
    schedule_interval="@daily",
    catchup=False,
) as dag:

    load_data_task = PythonOperator(
        task_id="load_csv_to_mysql",
        python_callable=load_csv_to_mysql
    )

    load_data_task
