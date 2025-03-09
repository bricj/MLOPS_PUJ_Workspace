from airflow import DAG
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.operators.python import PythonOperator
from datetime import datetime
import pandas as pd
import os
from airflow.utils.dates import days_ago

# Definir rutas de almacenamiento dentro del volumen compartido
DATA_OUTPUT = "/opt/airflow/models/"  # Directorio donde guardaremos el modelo

# Función para cargar datos desde MySQL
def load_data_from_mysql():
    mysql_hook = MySqlHook(mysql_conn_id="mysql_airflow_conn")  # Conexión en Airflow
    sql_query = "SELECT * FROM penguins;"  
    df = mysql_hook.get_pandas_df(sql_query)

    # Guardar copia local del DataFrame para debugging
    os.makedirs(DATA_OUTPUT, exist_ok=True)
    df.to_csv(DATA_OUTPUT + "penguins.csv", index=False)
    
    return df

# Definir el DAG
default_args = {
    "owner": "airflow",
    "start_date":days_ago(1),
    "retries": 1,
}

with DAG(
    dag_id="load_data_mysql",
    default_args=default_args,
    schedule_interval=None,  # Se ejecuta manualmente
    catchup=False,
) as dag:

    load_data_task = PythonOperator(
        task_id="load_data",
        python_callable=load_data_from_mysql
    )

    load_data_task