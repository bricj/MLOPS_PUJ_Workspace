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
    sql_query = "SELECT * FROM covertype_api;"  
    df = mysql_hook.get_pandas_df(sql_query) # Cargar datos guardados
    features = ['Elevation', 'Aspect', 'Slope', 'Horizontal_Distance_To_Hydrology',
       'Vertical_Distance_To_Hydrology', 'Horizontal_Distance_To_Roadways',
       'Hillshade_9am', 'Hillshade_Noon', 'Hillshade_3pm',
       'Horizontal_Distance_To_Fire_Points', 'Wilderness_Area', 'Soil_Type',
       'Cover_Type']
    
    # Eliminar datos inválidos
    df = df[features].dropna() # No hay evidencia de datos perdidos en el EDA
       
    variables_categoricas = ['Elevation', 'Aspect', 'Slope', 'Horizontal_Distance_To_Hydrology',
       'Vertical_Distance_To_Hydrology', 'Horizontal_Distance_To_Roadways',
       'Hillshade_9am', 'Hillshade_Noon', 'Hillshade_3pm',
       'Horizontal_Distance_To_Fire_Points', 'Wilderness_Area']
    
    variables_continuas = ['Wilderness_Area','Soil_Type',
       'Cover_Type']
    
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
            df.to_sql(name="covertype_proc", con=connection, if_exists="replace", index=False)


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
    description='Preprocesa los datos que se encuentran en la BBDD de airflow',
    schedule_interval=None,  # Se ejecuta manualmente
    catchup=False,
) as dag:

    #conectar funcion a dag
    preprocess_data_task = PythonOperator(
        task_id="transform_data",
        python_callable=clean_transform_data
    )

    preprocess_data_task