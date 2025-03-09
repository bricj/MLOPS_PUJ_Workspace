from airflow import DAG
from airflow.operators.python import PythonOperator
import pandas as pd
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from datetime import datetime
from airflow.utils.dates import days_ago

# Definir rutas de almacenamiento dentro del volumen compartido
DATA_OUTPUT = "/opt/airflow/models/"  # Directorio donde guardaremos el modelo

# Función para limpiar los datos
def clean_transform_data():
    df = pd.read_csv(DATA_OUTPUT + "penguins.csv")  # Cargar datos guardados
    features = ['species','island','culmen_length_mm','culmen_depth_mm',
                'flipper_length_mm','body_mass_g','sex']
    
    df = df[features].dropna()
    df = df[df['sex'] != '.']  # Eliminar datos inválidos
    #df.to_csv(DATA_OUTPUT + "penguins_clean.csv", index=False)
       
    variables_categoricas = ['species','island', 'sex']
    variables_continuas = ['culmen_length_mm','culmen_depth_mm','flipper_length_mm']
    
    le = LabelEncoder()
    for var in variables_categoricas:
        df[var] = le.fit_transform(df[var])
    
    scaler = MinMaxScaler()
    df[variables_continuas] = scaler.fit_transform(df[variables_continuas])
    
    df.to_csv(DATA_OUTPUT + "penguins_transformed.csv", index=False)

    return df

# Definir el DAG
default_args = {
    "owner": "airflow",
    "start_date":days_ago(1),
    "retries": 1,
}

with DAG(
    dag_id="clean_transform_data",
    default_args=default_args,
    schedule_interval=None,  # Se ejecuta manualmente
    catchup=False,
) as dag:

    preprocess_data_task = PythonOperator(
        task_id="transform_data",
        python_callable=clean_transform_data
    )

    preprocess_data_task