from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from datetime import datetime, timedelta
import requests
import pandas as pd
from sqlalchemy import text
from airflow.utils.dates import days_ago

API_URL = "http://fastapi:80/data?group_number=4"
#API_URL = "http://10.43.101.166:80/data?group_number=3"
TABLE_NAME = "covertype_api"


# Mapeo de nombres de columnas de la API a la base de datos
api_columns = [
    "col1", "col2", "col3", "col4", "col5", "col6", "col7", "col8", "col9", "col10", "col11", "col12", "col13"
]

db_columns = [
    "Elevation", "Aspect", "Slope", "Horizontal_Distance_To_Hydrology", "Vertical_Distance_To_Hydrology",
    "Horizontal_Distance_To_Roadways", "Hillshade_9am", "Hillshade_Noon", "Hillshade_3pm",
    "Horizontal_Distance_To_Fire_Points", "Wilderness_Area", "Soil_Type", "Cover_Type", "batch_number"
]

# Función para obtener los datos desde la API
def fetch_data():
    response = requests.get(API_URL)
    response.raise_for_status()
    print(response.status_code)
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
    
    with engine.connect() as connection:
        for record in records:
            mapped_record = dict(zip(db_columns[:-1], record))  # Mapear valores con nombres de columnas
            mapped_record["batch_number"] = batch_number  # Añadir batch_number
            
            values_placeholders = ", ".join([":%s" % col for col in db_columns])
            update_values = ", ".join([f"{col}=VALUES({col})" for col in db_columns])
            
            sql = text(f"""
            INSERT INTO {TABLE_NAME} ({', '.join(db_columns)})
            VALUES ({values_placeholders})
            ON DUPLICATE KEY UPDATE {update_values};
            """)
            
            connection.execute(sql, mapped_record)


# Definición del DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'retries': 1#,
    #'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='fetch_and_store_data',
    default_args=default_args,
    description='Obtiene datos de una API y los almacena en MySQL',
    schedule_interval=timedelta(minutes=1),  # Ejecutar cada 1 minutos
    #schedule_interval=None, 
    catchup=False
) as dag:

    store_data_task = PythonOperator(
        task_id='store_data',
        python_callable=store_data,
        dag=dag,
    )

    store_data_task
