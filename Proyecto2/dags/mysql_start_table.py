from airflow import DAG
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.operators.python import PythonOperator
from datetime import datetime
from airflow.utils.dates import days_ago

# Función para eliminar la tabla en MySQL
def start_table():

    #conectar a mysql
    mysql_hook = MySqlHook(mysql_conn_id="mysql_airflow_conn")  # Conexión definida en Airflow
    engine = mysql_hook.get_sqlalchemy_engine()

    #queries para eliminar tablas
    drop_table_query = "DROP TABLE IF EXISTS suelos;"
    drop_table_query_2 = "DROP TABLE IF EXISTS suelos_proc;"

    create_table_query = """
        CREATE TABLE IF NOT EXISTS suelos (
            Elevation FLOAT,
            Aspect FLOAT,
            Slope FLOAT,
            Horizontal_Distance_To_Hydrology FLOAT,
            Vertical_Distance_To_Hydrology FLOAT,
            Horizontal_Distance_To_Roadways FLOAT,
            Hillshade_9am FLOAT,
            Hillshade_Noon FLOAT,
            Hillshade_3pm FLOAT,
            Horizontal_Distance_To_Fire_Points FLOAT,
            Wilderness_Area VARCHAR(20),
            Soil_Type VARCHAR(20),
            Cover_Type INTEGER,
            batch_number INTEGER
        )
        """
        
        
        #ejecutar query
    with engine.begin() as connection:
        connection.execute(drop_table_query)
        connection.execute(drop_table_query_2)
        connection.execute(create_table_query)

# Definir el DAG
default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
    "retries": 1,
}

#crear dag
with DAG(
    dag_id="iniciar_tabla_mysql",
    default_args=default_args,
    schedule_interval=None,  # Solo se ejecuta manualmente
    catchup=False,
) as dag:

    #conectar funcion a dag
    start_table_task = PythonOperator(
        task_id="start_table",
        python_callable=start_table
    )

    start_table_task