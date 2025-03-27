from airflow import DAG
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.operators.python import PythonOperator
from datetime import datetime
import pandas as pd
import logging
from airflow.utils.dates import days_ago

# Ruta del archivo en el volumen compartido
FILE_PATH = "/opt/airflow/data/penguins_size.csv"

# Función para leer el archivo y cargarlo en MySQL
def load_csv_to_mysql():
    try:
        # Conectar a MySQL
        mysql_hook = MySqlHook(mysql_conn_id="mysql_airflow_conn")  # Asegúrate de definir esta conexión en Airflow
        engine = mysql_hook.get_sqlalchemy_engine()

        # Leer el archivo CSV
        df = pd.read_csv(FILE_PATH)

        # Validación de columnas esperadas
        expected_columns = {
            "species", "island", "culmen_length_mm", "culmen_depth_mm",
            "flipper_length_mm", "body_mass_g", "sex"
        }
        if not expected_columns.issubset(df.columns):
            raise ValueError(f"El CSV no contiene las columnas esperadas: {expected_columns}")

        # Crear la tabla en MySQL si no existe
        create_table_query = """
        CREATE TABLE IF NOT EXISTS penguins (
            species VARCHAR(20),
            island VARCHAR(20),
            culmen_length_mm FLOAT,
            culmen_depth_mm FLOAT,
            flipper_length_mm FLOAT,
            body_mass_g FLOAT,
            sex VARCHAR(20)
        )
        """
        create_table_query_1 = """
        CREATE TABLE IF NOT EXISTS penguins_api (
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
            Wilderness_Area FLOAT, 
            Soil_Type VARCHAR(20), 
            Cover_Type VARCHAR(20), 
            batch_number FLOAT
        )
        """
        
        #ejecutar query
        with engine.begin() as connection:
            connection.execute(create_table_query)
            connection.execute(create_table_query_1)
            df.to_sql(name="penguins", con=connection, if_exists="replace", index=False)

        logging.info("Datos cargados exitosamente en MySQL.")

    except Exception as e:
        logging.error(f"Error en la carga de datos a MySQL: {e}")
        raise

# Definir el DAG
default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
    "retries": 1,
}

#crear dag
with DAG(
    dag_id="crear_tabla_mysql",
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
) as dag:

    #conectar funcion a dag
    load_data_task = PythonOperator(
        task_id="load_csv_to_mysql",
        python_callable=load_csv_to_mysql
    )

    load_data_task
    