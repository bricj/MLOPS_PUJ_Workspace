from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.task_group import TaskGroup
from datetime import datetime, timedelta
import requests
import pandas as pd
import json
import logging
from sqlalchemy import text
from airflow.utils.dates import days_ago

from airflow.models import Variable  # Importar módulo de Variables

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("diabetes_data_pipeline")


# Configuración de la API usando la URL específica PARA MINIKUBE
API_BASE_URL = "http://10.43.101.168:32569"
logger.info(f"Using API endpoint: {API_BASE_URL}")


# Nombre de las tablas en la BD
TRAIN_TABLE = "diabetes_train"
VALIDATION_TABLE = "diabetes_validation"
TEST_TABLE = "diabetes_test"

# Argumentos por defecto para el DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'retries': 1,
}

# Función para obtener un batch específico y guardarlo en MySQL
def fetch_and_store_batch(dataset_type, batch_number, **kwargs):
    """Obtiene un batch de datos específico y lo guarda en MySQL"""
    try:
        # Determinar el endpoint y la tabla según el tipo de dataset
        endpoint = ""
        table_name = ""
        
        if dataset_type == 'train':
            endpoint = f"/get-batch/?batch_number={batch_number}"
            table_name = TRAIN_TABLE
        elif dataset_type == 'validation':
            endpoint = f"/get-validation-batch/?batch_number={batch_number}"
            table_name = VALIDATION_TABLE
        elif dataset_type == 'test':
            endpoint = f"/get-test-batch/?batch_number={batch_number}"
            table_name = TEST_TABLE
        else:
            raise ValueError(f"Tipo de dataset no válido: {dataset_type}")
        
        # Realizar petición a la API
        print(f"Obteniendo {dataset_type} batch {batch_number} desde {API_BASE_URL}{endpoint}")
        response = requests.get(f"{API_BASE_URL}{endpoint}")
        response.raise_for_status()
        
        # Obtener datos
        batch_data = response.json()
        
        # Verificar si es un diccionario con clave 'data' o directamente una lista
        if isinstance(batch_data, dict) and 'data' in batch_data:
            records = batch_data['data']
        else:
            records = batch_data  # Asumir que es directamente una lista de registros
        
        if not records:
            print(f"No hay datos en {dataset_type} batch {batch_number}")
            return 0
            
        print(f"Obtenidos {len(records)} registros de {dataset_type} batch {batch_number}")
        
        # Connect to PostgreSQL
        postgres_hook = PostgresHook(postgres_conn_id="postgres_airflow_conn")  # Change to your actual connection ID
        engine = postgres_hook.get_sqlalchemy_engine()
        
        # Convertir registros a DataFrame para facilitar la inserción
        df = pd.DataFrame(records)

        # Renombrar columnas problemáticas como 'change' que son palabras reservadas en SQL
        if 'change' in df.columns:
            df.rename(columns={'change': 'change_column'}, inplace=True)

        with engine.begin() as connection:
            rows_inserted = 0
            for _, row in df.iterrows():
                # Filtrar valores None y crear un diccionario limpio
                clean_row = {}
                for column, value in row.items():
                    if pd.isna(value) or value =='?':
                        # Omitir valores nulos o establecer un valor predeterminado
                        # clean_row[column] = None  # Opción 1: Incluir como NULL
                        pass  # Opción 2: Omitir columna
                    else:
                        clean_row[column.replace('-','_')] = value
                
                if not clean_row:
                    continue
                
                # Construir la consulta SQL con parámetros nombrados
                columns_str = ', '.join(clean_row.keys())
                placeholders_str = ', '.join([f':{col}' for col in clean_row.keys()])
                sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders_str})"
                
                # Ejecutar la consulta con parámetros nombrados
                connection.execute(text(sql), clean_row)
                rows_inserted += 1
            
            print(f"Insertados {rows_inserted} registros en tabla {table_name} para {dataset_type} batch {batch_number} usando método fila por fila")
            return rows_inserted
        
    except Exception as e:
        print(f"Error procesando {dataset_type} batch {batch_number}: {str(e)}")
        raise
    
# Función principal para procesar todos los batches de un tipo de dataset
def process_dataset(dataset_type, batches, **kwargs):
    """Procesa todos los batches de un tipo específico de dataset"""
    ti = kwargs['ti']
        
    print(f"Procesando {batches} batches para {dataset_type}")
    
    total_records = 0
    for batch_number in range(batches):
        records_inserted = fetch_and_store_batch(
            dataset_type=dataset_type,
            batch_number=batch_number,
            **kwargs
        )
        total_records += records_inserted
        
    print(f"Completado procesamiento de {dataset_type}: {total_records} registros en total")
    return total_records

# Definición del DAG
with DAG(
    dag_id='fetch_and_store_diabetes_data',
    default_args=default_args,
    description='Obtiene datos de la API FastAPI y los almacena en MySQL',
    schedule_interval=None,  # Manual trigger
    catchup=False
) as dag:
        
    # Procesar batches de entrenamiento
    process_train_task = PythonOperator(
        task_id='process_train_batches',
        python_callable=process_dataset,
        op_kwargs={'dataset_type': 'train', 'batches':5},
        dag=dag,
    )

    # Procesar batches de validación
    process_validation_task = PythonOperator(
        task_id='process_validation_batches',
        python_callable=process_dataset,
        op_kwargs={'dataset_type': 'validation', 'batches':2},
        dag=dag,
    )

        # Procesar batches de prueba
    process_test_task = PythonOperator(
        task_id='process_test_batches',
        python_callable=process_dataset,
        op_kwargs={'dataset_type': 'test', 'batches':2},
        dag=dag,
        )
        
    # Definir dependencias entre tareas y grupos
    process_train_task >> process_validation_task >> process_test_task
