from airflow import DAG
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.operators.python import PythonOperator
from datetime import datetime
from airflow.utils.dates import days_ago

# Función para eliminar la tabla en MySQL
def drop_table():

    #conectar a mysql
    mysql_hook = MySqlHook(mysql_conn_id="mysql_airflow_conn")  # Conexión definida en Airflow
    engine = mysql_hook.get_sqlalchemy_engine()

    #queries para eliminar tablas
    drop_table_query = "DROP TABLE IF EXISTS penguins;"
    drop_table_query_2 = "DROP TABLE IF EXISTS penguins_proc;"

    #ejecutar queries
    with engine.begin() as connection:
        connection.execute(drop_table_query)
        connection.execute(drop_table_query_2)

# Definir el DAG
default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
    "retries": 1,
}

#crear dag
with DAG(
    dag_id="eliminar_tabla_mysql",
    default_args=default_args,
    schedule_interval=None,  # Solo se ejecuta manualmente
    catchup=False,
) as dag:

    #conectar funcion a dag
    drop_table_task = PythonOperator(
        task_id="drop_table",
        python_callable=drop_table
    )

    drop_table_task