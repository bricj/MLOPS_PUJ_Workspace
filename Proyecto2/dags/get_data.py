from airflow import DAG
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import requests
from sqlalchemy.sql import text
from airflow.utils.dates import days_ago

# Función para obtener y guardar datos
def get_data():
    url_template = "http://10.43.101.166:80/data?group_number=6"
    TABLE_NAME = "covertype_api"      

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
        for batch in range(1, 11):  # Ejecutar 10 veces
            try:
                url = url_template.format(batch)
                r = requests.get(url, timeout=10)
                r.raise_for_status()
                d = r.json()
                data = d.get('data', [])
                batch_number = d.get('batch_number', batch)  # Si no existe, asigna el número de iteración
                
                for record in data:
                    record.append(batch_number)  # Agregar batch_number al final
                    connection.execute(sql, dict(zip(columns, record)))

                print(f"✅ Se ha cargado el batch {batch_number} con {len(data)} registros")
            except requests.exceptions.RequestException as e:
                print(f"❌ Error en la API (batch {batch}): {e}")
    
# Definir el DAG
default_args = {
    "owner": "airflow",
    "start_date": days_ago(0),
    "retries": 1,
    "retry_delay": timedelta(minutes=1)
}

with DAG(
    dag_id="data_api",
    default_args=default_args,
    schedule_interval="@daily",  # Ejecutar 1 vez al día (dentro ejecuta 10 veces)
    max_active_runs=1,
    catchup=False,
) as dag:

    load_table_task = PythonOperator(
        task_id="g_data_api",
        python_callable=get_data
    )

    load_table_task
