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
    drop_table_query = "DROP TABLE IF EXISTS diabetes;"
    drop_table_query_2 = "DROP TABLE IF EXISTS processed_diabetes;"

    create_table_query = """
        CREATE TABLE IF NOT EXISTS diabetes (
            encounter_id INT NOT NULL,
            patient_nbr INT NOT NULL,
            race VARCHAR(50) NOT NULL,
            gender VARCHAR(20) NOT NULL,
            age VARCHAR(20) NOT NULL,
            weight FLOAT,
            admission_type_id INT NOT NULL,
            discharge_disposition_id INT NOT NULL,
            admission_source_id INT NOT NULL,
            time_in_hospital INT NOT NULL,
            payer_code INT,
            medical_specialty INT,
            num_lab_procedures INT NOT NULL,
            num_procedures INT NOT NULL,
            num_medications INT NOT NULL,
            number_outpatient INT NOT NULL,
            number_emergency INT NOT NULL,
            number_inpatient INT NOT NULL,
            diag_1 VARCHAR(10),
            diag_2 VARCHAR(10),
            diag_3 VARCHAR(10),
            number_diagnoses INT NOT NULL,
            max_glu_serum VARCHAR(20) NOT NULL,
            A1Cresult VARCHAR(20) NOT NULL,
            metformin VARCHAR(20) NOT NULL,
            repaglinide VARCHAR(20) NOT NULL,
            nateglinide VARCHAR(20) NOT NULL,
            chlorpropamide VARCHAR(20) NOT NULL,
            glimepiride VARCHAR(20) NOT NULL,
            acetohexamide VARCHAR(20) NOT NULL,
            glipizide VARCHAR(20) NOT NULL,
            glyburide VARCHAR(20) NOT NULL,
            tolbutamide VARCHAR(20) NOT NULL,
            pioglitazone VARCHAR(20) NOT NULL,
            rosiglitazone VARCHAR(20) NOT NULL,
            acarbose VARCHAR(20) NOT NULL,
            miglitol VARCHAR(20) NOT NULL,
            troglitazone VARCHAR(20) NOT NULL,
            tolazamide VARCHAR(20) NOT NULL,
            examide VARCHAR(20) NOT NULL,
            citoglipton VARCHAR(20) NOT NULL,
            insulin VARCHAR(20) NOT NULL,
            glyburide_metformin VARCHAR(20) NOT NULL,
            glipizide_metformin VARCHAR(20) NOT NULL,
            glimepiride_pioglitazone VARCHAR(20) NOT NULL,
            metformin_rosiglitazone VARCHAR(20) NOT NULL,
            metformin_pioglitazone VARCHAR(20) NOT NULL,
            change_column VARCHAR(20) NOT NULL,
            diabetesMed VARCHAR(20) NOT NULL,
            readmitted VARCHAR(20) NOT NULL
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