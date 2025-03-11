from airflow import DAG
from airflow.operators.python import PythonOperator
import pandas as pd
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from datetime import datetime
from airflow.utils.dates import days_ago
from airflow.providers.mysql.hooks.mysql import MySqlHook

# Definir rutas de almacenamiento dentro del volumen compartido
DATA_OUTPUT = "/opt/airflow/models/"  # Directorio donde guardaremos el modelo

# Función para limpiar los datos
def clean_transform_data():

    # Conectar a MySQL
    mysql_hook = MySqlHook(mysql_conn_id="mysql_airflow_conn")  # Asegúrate de definir esta conexión en Airflow
    engine = mysql_hook.get_sqlalchemy_engine()

    #cargar dataframe de mysql
    sql_query = "SELECT * FROM penguins;"  
    df = mysql_hook.get_pandas_df(sql_query) # Cargar datos guardados
    features = ['species','island','culmen_length_mm','culmen_depth_mm',
                'flipper_length_mm','body_mass_g','sex']
    
    # Eliminar datos inválidos
    df = df[features].dropna()
    df = df[df['sex'] != '.']  
       
    variables_categoricas = ['species','island', 'sex']
    variables_continuas = ['culmen_length_mm','culmen_depth_mm','flipper_length_mm']
    
    # codificacion n a 1
    le = LabelEncoder()
    for var in variables_categoricas:
        df[var] = le.fit_transform(df[var])
    
    # normalizacion
    scaler = MinMaxScaler()
    df[variables_continuas] = scaler.fit_transform(df[variables_continuas])

    #query para crear tabla de datos procesados
    create_table_query = """
        CREATE TABLE IF NOT EXISTS penguins_proc (
            species INTEGER,
            island INTEGER,
            culmen_length_mm FLOAT,
            culmen_depth_mm FLOAT,
            flipper_length_mm FLOAT,
            body_mass_g FLOAT,
            sex INTEGER
        )
        """
    
    #ejecutar query
    with engine.begin() as connection:
            connection.execute(create_table_query)
            df.to_sql(name="penguins_proc", con=connection, if_exists="replace", index=False)

# Definir el DAG
default_args = {
    "owner": "airflow",
    "start_date":days_ago(1),
    "retries": 1,
}

#crear dag
with DAG(
    dag_id="clean_transform_data",
    default_args=default_args,
    schedule_interval=None,  # Se ejecuta manualmente
    catchup=False,
) as dag:

    #conectar funcion a dag
    preprocess_data_task = PythonOperator(
        task_id="transform_data",
        python_callable=clean_transform_data
    )

    preprocess_data_task