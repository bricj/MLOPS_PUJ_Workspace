from airflow import DAG
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.utils.dates import days_ago
from airflow.operators.python import PythonOperator
import time

# definir dag
default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
    "retries": 1
}

def trigger_dag_repeatedly(dag_run, **kwargs):
    """Función que dispara un DAG hijo 10 veces con 1 minuto de intervalo."""
    from airflow.models import DagRun
    from airflow.utils.state import State

    dag_id = "fetch_and_store_data" #dag_hijo
    execution_date = kwargs["execution_date"]

    for i in range(10):
        dr = DagRun(
            dag_id=dag_id,
            execution_date=execution_date,
            state=State.RUNNING
        )
        dr.run()
        time.sleep(60)  # Espera 1 minuto entre ejecuciones



#crear dag
with DAG(
    dag_id="dag_maestro",
    default_args=default_args,
    description='Orquestador del flujo operativo del modelo machine learning',
    schedule_interval="@daily",
    catchup=False,
) as dag:
    
    trigger_dag_hijo = PythonOperator(
        task_id="trigger_dag_hijo",
        python_callable=trigger_dag_repeatedly,
        provide_context=True
    )

    #funcion que sube los datos a mysql
    t1 = TriggerDagRunOperator(
        task_id="store_data",
        trigger_dag_id="fetch_and_store_data",
        wait_for_completion=True,
    )

    #funcion que procesa datos
    t2 = TriggerDagRunOperator(
        task_id="transform_data",
        trigger_dag_id="clean_transform_data",
        wait_for_completion=True,
    )

    #funcion que entrena modelo
    t3 = TriggerDagRunOperator(
        task_id="train_model",
        trigger_dag_id="train_model_penguins",
        wait_for_completion=True,
    )

    #funcion que elimina tablas
    t4 = TriggerDagRunOperator(
        task_id="drop_table",
        trigger_dag_id="eliminar_tabla_mysql",
        wait_for_completion=True,
    )

    # Definir el orden de ejecución
    t4 >> t1 >> t2 >> t3