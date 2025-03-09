from airflow import DAG
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.utils.dates import days_ago

default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
    "retries": 1
}

with DAG(
    dag_id="dag_maestro",
    default_args=default_args,
    schedule_interval="@daily",
    catchup=False,
) as dag:

    t1 = TriggerDagRunOperator(
        task_id="load_csv_to_mysql",
        trigger_dag_id="crear_tabla_mysql",
        wait_for_completion=True,
    )

    t2 = TriggerDagRunOperator(
        task_id="load_data",
        trigger_dag_id="load_data_mysql",
        wait_for_completion=True,
    )


    t3 = TriggerDagRunOperator(
        task_id="transform_data",
        trigger_dag_id="clean_transform_data",
        wait_for_completion=True,
    )

    t4 = TriggerDagRunOperator(
        task_id="train_model",
        trigger_dag_id="train_model_penguins",
        wait_for_completion=True,
    )

    t6 = TriggerDagRunOperator(
        task_id="drop_table",
        trigger_dag_id="eliminar_tabla_mysql",
        wait_for_completion=True,
    )

    # Definir el orden de ejecución
    t1 >> t2 >> t3 >> t4 >> t6
