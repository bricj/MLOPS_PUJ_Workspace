from airflow import DAG
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator
from datetime import datetime
from airflow.utils.dates import days_ago

# Función para eliminar la tabla en MySQL
def start_table():

    # Connect to PostgreSQL
    postgres_hook = PostgresHook(postgres_conn_id="postgres_airflow_conn")  # Change to your actual connection ID
    engine = postgres_hook.get_sqlalchemy_engine()

    #queries para eliminar tablas
    drop_table_query = "DROP TABLE IF EXISTS diabetes_train;"
    drop_table_query_2 = "DROP TABLE IF EXISTS processed_diabetes;"
    drop_table_query_2 = "DROP TABLE IF EXISTS processed_diabetes;"

    def borrar_tabla(table_name):
        return f"DROP TABLE IF EXISTS {table_name};"

    def query_ese(table_name):
        return f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            encounter_id INT,
            patient_nbr INT,
            race VARCHAR(50),
            gender VARCHAR(20),
            age VARCHAR(20),
            weight VARCHAR(20),
            admission_type_id INT,
            discharge_disposition_id INT,
            admission_source_id INT,
            time_in_hospital INT,
            payer_code VARCHAR(10),
            medical_specialty VARCHAR(50),
            num_lab_procedures INT,
            num_procedures INT,
            num_medications INT,
            number_outpatient INT,
            number_emergency INT,
            number_inpatient INT,
            diag_1 VARCHAR(10),
            diag_2 VARCHAR(10),
            diag_3 VARCHAR(10),
            number_diagnoses INT,
            max_glu_serum VARCHAR(20),
            A1Cresult VARCHAR(20),
            metformin VARCHAR(20),
            repaglinide VARCHAR(20),
            nateglinide VARCHAR(20),
            chlorpropamide VARCHAR(20),
            glimepiride VARCHAR(20),
            acetohexamide VARCHAR(20),
            glipizide VARCHAR(20),
            glyburide VARCHAR(20),
            tolbutamide VARCHAR(20),
            pioglitazone VARCHAR(20),
            rosiglitazone VARCHAR(20),
            acarbose VARCHAR(20),
            miglitol VARCHAR(20),
            troglitazone VARCHAR(20),
            tolazamide VARCHAR(20),
            examide VARCHAR(20),
            citoglipton VARCHAR(20),
            insulin VARCHAR(20),
            glyburide_metformin VARCHAR(20),
            glipizide_metformin VARCHAR(20),
            glimepiride_pioglitazone VARCHAR(20),
            metformin_rosiglitazone VARCHAR(20),
            metformin_pioglitazone VARCHAR(20),
            change_column VARCHAR(20),
            diabetesMed VARCHAR(20),
            readmitted VARCHAR(20)
            )
            """
    
    
        
        #ejecutar query
    with engine.begin() as connection:
        connection.execute(borrar_tabla('diabetes_train'))
        connection.execute(borrar_tabla('diabetes_validation'))
        connection.execute(borrar_tabla('diabetes_test'))
        connection.execute(query_ese('diabetes_train'))
        connection.execute(query_ese('diabetes_validation'))
        connection.execute(query_ese('diabetes_test'))

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