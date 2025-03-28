from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from datetime import datetime, timedelta
import requests
import pymysql
import pandas as pd

API_URL = "http://localhost:80/data?group_number=2"
TABLE_NAME = "penguins_api"

# Función para obtener los datos desde la API
def fetch_data():
    response = requests.get(API_URL)
    response.raise_for_status()
    return response.json()

# Función para almacenar los datos en MySQL
def store_data():

    # Conectar a MySQL
    mysql_hook = MySqlHook(mysql_conn_id="mysql_airflow_conn")  # Asegúrate de definir esta conexión en Airflow
    engine = mysql_hook.get_sqlalchemy_engine()

    data = fetch_data()
    group_number = data["group_number"]
    batch_number = data["batch_number"]
    records = data["data"]
    
    for record in records:
        record.append(batch_number)  # Añadir batch_number al final

        columns = ["Elevation", "Aspect", "Slope", "Horizontal_Distance_To_Hydrology", "Vertical_Distance_To_Hydrology", "Horizontal_Distance_To_Roadways", "Hillshade_9am", "Hillshade_Noon", "Hillshade_3pm", "Horizontal_Distance_To_Fire_Points", "Wilderness_Area", "Soil_Type", "Cover_Type", "batch_number"]
        values_placeholders = ", ".join(["%s"] * len(columns))
        update_values = ", ".join([f"{col}=VALUES({col})" for col in columns])
        
        sql = text(f"""
            INSERT INTO {TABLE_NAME} ({', '.join(columns)})
            VALUES ({values_placeholders})
            ON DUPLICATE KEY UPDATE {update_values};
            """)
            
        connection.execute(sql, dict(zip(columns, record)))


# Definición del DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 3, 26),
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'fetch_and_store_data',
    default_args=default_args,
    description='Obtiene datos de una API y los almacena en MySQL',
    schedule_interval=timedelta(days=1),
)

store_data_task = PythonOperator(
    task_id='store_data',
    python_callable=store_data,
    dag=dag,
)

store_data_task
