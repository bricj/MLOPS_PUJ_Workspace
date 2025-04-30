from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from datetime import datetime, timedelta
import requests
import pandas as pd
from sqlalchemy import text
from airflow.utils.dates import days_ago


TABLE_NAME = "diabetes"

# Mapeo de nombres de columnas de la API a la base de datos
api_columns = [
    "col1", "col2", "col3", "col4", "col5", "col6", "col7", "col8", "col9", "col10", 
    "col11", "col12", "col13", "col14", "col15", "col16", "col17", "col18", "col19", 
    "col20", "col21", "col22", "col23", "col24", "col25", "col26", "col27", "col28", 
    "col29", "col30", "col31", "col32", "col33", "col34", "col35", "col36", "col37", 
    "col38", "col39", "col40", "col41", "col42", "col43", "col44", "col45", "col46", 
    "col47", "col48", "col49", "col50"
]

db_columns = [
    "encounter_id", "patient_nbr", "race", "gender", "age", "weight", "admission_type_id", 
    "discharge_disposition_id", "admission_source_id", "time_in_hospital", "payer_code", 
    "medical_specialty", "num_lab_procedures", "num_procedures", "num_medications", 
    "number_outpatient", "number_emergency", "number_inpatient", "diag_1", "diag_2", "diag_3", 
    "number_diagnoses", "max_glu_serum", "A1Cresult", "metformin", "repaglinide", "nateglinide", 
    "chlorpropamide", "glimepiride", "acetohexamide", "glipizide", "glyburide", "tolbutamide", 
    "pioglitazone", "rosiglitazone", "acarbose", "miglitol", "troglitazone", "tolazamide", "examide", 
    "citoglipton", "insulin", "glyburide_metformin", "glipizide_metformin", "glimepiride_pioglitazone", 
    "metformin_rosiglitazone", "metformin_pioglitazone", "change", "diabetesMed", "readmitted"
]

# Función para obtener los datos desde la API
def fetch_data(group_number):
    requests.get(f"http://datapi:80/restart_data_generation?group_number={group_number}")
    response = requests.get(f"http://datapi:80/data?group_number={group_number}")
    response.raise_for_status()
    print(response.status_code)
    return response.json()

# Función para almacenar los datos en MySQL
def store_data():

    # Conectar a MySQL
    mysql_hook = MySqlHook(mysql_conn_id="mysql_airflow_conn")  # Asegúrate de definir esta conexión en Airflow
    engine = mysql_hook.get_sqlalchemy_engine()

    for group_number in range(1,10):

        data = fetch_data(group_number)
        batch_number = data["batch_number"]
        records = data["data"]
        
        with engine.connect() as connection:

            for record in records:

                mapped_record = dict(zip(db_columns[:-1], record))  # Mapear valores con nombres de columnas
                mapped_record["batch_number"] = batch_number  # Añadir batch_number
                
                values_placeholders = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in list(mapped_record.values())])
                update_values = ", ".join([f"{col}=VALUES({col})" for col in db_columns])
                
                sql = text(f"""
                INSERT INTO {TABLE_NAME} ({', '.join(db_columns)})
                VALUES ({values_placeholders})
                ON DUPLICATE KEY UPDATE {update_values};
                """)
                
                connection.execute(sql)

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
    schedule_interval=None,  
    catchup=False
) as dag:

    store_data_task = PythonOperator(
        task_id='store_data',
        python_callable=store_data,
        dag=dag,
    )

    store_data_task
