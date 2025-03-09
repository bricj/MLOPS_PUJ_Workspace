from airflow import DAG
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.operators.python import PythonOperator
from datetime import datetime
from airflow.utils.dates import days_ago

# Función para eliminar la tabla en MySQL
def drop_table():
    mysql_hook = MySqlHook(mysql_conn_id="mysql_airflow_conn")  # Conexión definida en Airflow
    engine = mysql_hook.get_sqlalchemy_engine()

    drop_table_query = "DROP TABLE IF EXISTS penguins;"

    with engine.begin() as connection:
        connection.execute(drop_table_query)

# Definir el DAG
default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
    "retries": 1,
}

with DAG(
    dag_id="eliminar_tabla_mysql",
    default_args=default_args,
    schedule_interval=None,  # Solo se ejecuta manualmente
    catchup=False,
) as dag:

    drop_table_task = PythonOperator(
        task_id="drop_table",
        python_callable=drop_table
    )

    drop_table_task