from airflow import DAG
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.utils.dates import days_ago

# definir dag
default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
    "retries": 1
}

#crear dag
with DAG(
    dag_id="dag_maestro",
    default_args=default_args,
    schedule_interval="@daily",
    catchup=False,
) as dag:

    #funcion que sube los datos a mysql
    t1 = TriggerDagRunOperator(
        task_id="load_csv_to_mysql",
        trigger_dag_id="crear_tabla_mysql",
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
    t1 >> t2 >> t3 >> t4
