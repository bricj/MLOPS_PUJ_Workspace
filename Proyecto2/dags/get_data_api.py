from airflow import DAG
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.operators.python import PythonOperator
from datetime import datetime
from airflow.utils.dates import days_ago

import requests
import json
import readline

import requests
from sqlalchemy.sql import text
from airflow.providers.mysql.hooks.mysql import MySqlHook



# Función 
def get_data():
    #url = 'http://10.43.101.149:80/data?group_number=3'
    url = "http://10.43.101.166:80/data?group_number=2"
    TABLE_NAME = "covertype_api"      

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        d = r.json()
        data = d.get('data', [])  # Corrección aquí
        group_number = d.get('group_number', None)
        batch_number = d.get('batch_number', None)
        #data = d.get('data', [{}])[0]
        #return json.dumps(data)  # Serializar para XCom
    except requests.exceptions.RequestException as e:
        print(f"Error en la API: {e}")
        return  # Termina la ejecución para evitar errores   
        #return json.dumps({"error": str(e)})  # Evita errores en XCom 

    # Conectar a MySQL
    mysql_hook = MySqlHook(mysql_conn_id="mysql_airflow_conn")  
    engine = mysql_hook.get_sqlalchemy_engine()

    columns = [
        "Elevation", "Aspect", "Slope", "Horizontal_Distance_To_Hydrology",
        "Vertical_Distance_To_Hydrology", "Horizontal_Distance_To_Roadways",
        "Hillshade_9am", "Hillshade_Noon", "Hillshade_3pm",
        "Horizontal_Distance_To_Fire_Points", "Wilderness_Area", "Soil_Type",
        "Cover_Type", "batch_number"
    ]
    
    values_placeholders = ", ".join(["%s"] * len(columns))
    update_values = ", ".join([f"{col}=VALUES({col})" for col in columns])

    sql = text(f"""
        INSERT INTO {TABLE_NAME} ({', '.join(columns)})
        VALUES ({values_placeholders})
        ON DUPLICATE KEY UPDATE {update_values};
    """)

    with engine.connect() as connection:
        for record in data:
            record.append(batch_number)  # Agregar batch_number al final
            connection.execute(sql, dict(zip(columns, record)))

    return print(
        f"Se ha cargado el batch {batch_number} de la tabla de datos original")

# Definir el DAG
default_args = {
    "owner": "airflow",
    "start_date": days_ago(0),
    "retries": 1,
}

#crear dag
with DAG(
    dag_id="load_data_api",
    default_args=default_args,
    schedule_interval="*/1 * * * *",
    max_active_runs=1,
    catchup=False,
) as dag:

    #conectar funcion a dag
    load_table_task = PythonOperator(
        task_id="get_data_api",
        python_callable=get_data
    )

    load_table_task