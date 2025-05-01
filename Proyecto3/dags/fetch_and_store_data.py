from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.utils.task_group import TaskGroup
from datetime import datetime, timedelta
import requests
import pandas as pd
import json
import logging
from sqlalchemy import text
from airflow.utils.dates import days_ago

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("diabetes_data_pipeline")

# Configuración de la API
API_HOST = "datapi"  # nombre del servicio Docker
API_PORT = 80
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

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
    'retries': 3,
    'retry_delay': timedelta(minutes=2),
}

# Función para obtener información del dataset
def get_dataset_info(**kwargs):
    """Obtiene información sobre los datasets y la guarda en XCom"""
    try:
        # Realizar petición a la API
        response = requests.get(f"{API_BASE_URL}/dataset-info")
        response.raise_for_status()
        
        # Obtener datos
        dataset_info = response.json()
        logger.info(f"Información del dataset: {dataset_info}")
        
        # Guardar en XCom para uso posterior
        ti = kwargs['ti']
        ti.xcom_push(key='train_size', value=dataset_info['train_size'])
        ti.xcom_push(key='validation_size', value=dataset_info['validation_size'])
        ti.xcom_push(key='test_size', value=dataset_info['test_size'])
        ti.xcom_push(key='batch_size', value=dataset_info['batch_size'])
        
        return dataset_info
    except Exception as e:
        logger.error(f"Error al obtener información del dataset: {str(e)}")
        raise

# Función para obtener el número total de batches
def get_total_batches(dataset_type, **kwargs):
    """Obtiene el número total de batches para un tipo de dataset específico"""
    try:
        endpoint = ""
        if dataset_type == 'train':
            endpoint = "/get-total-batches/"
        elif dataset_type == 'validation':
            endpoint = "/get-total-validation-batches/"
        elif dataset_type == 'test':
            endpoint = "/get-total-test-batches/"
        else:
            raise ValueError(f"Tipo de dataset no válido: {dataset_type}")
            
        # Realizar petición a la API
        response = requests.post(f"{API_BASE_URL}{endpoint}")
        response.raise_for_status()
        
        # Obtener datos
        result = response.json()
        total_batches = result['total_batches']
        logger.info(f"Total de batches para {dataset_type}: {total_batches}")
        
        # Guardar en XCom para uso posterior
        ti = kwargs['ti']
        ti.xcom_push(key=f'total_{dataset_type}_batches', value=total_batches)
        
        return total_batches
    except Exception as e:
        logger.error(f"Error al obtener total de batches para {dataset_type}: {str(e)}")
        raise

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
        logger.info(f"Obteniendo {dataset_type} batch {batch_number} desde {API_BASE_URL}{endpoint}")
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
            logger.warning(f"No hay datos en {dataset_type} batch {batch_number}")
            return 0
            
        logger.info(f"Obtenidos {len(records)} registros de {dataset_type} batch {batch_number}")
        
        # Conectar a MySQL
        mysql_hook = MySqlHook(mysql_conn_id="mysql_diabetes_conn")
        engine = mysql_hook.get_sqlalchemy_engine()
        
        # Convertir registros a DataFrame para facilitar la inserción
        df = pd.DataFrame(records)

        # Renombrar columnas problemáticas como 'change' que son palabras reservadas en SQL
        if 'change' in df.columns:
            df.rename(columns={'change': 'change_column'}, inplace=True)
        
        # Añadir columna de batch_number
        df['batch_number'] = batch_number
        
        # CORRECCIÓN: Usar df.to_sql() en lugar de construir la consulta SQL manualmente
        # Esto deja que SQLAlchemy maneje correctamente los tipos y valores nulos
        try:
            # Método 1: Usar to_sql para insertar todos los datos de una vez
            rows_inserted = len(df)
            df.to_sql(
                name=table_name,
                con=engine,
                if_exists='append',  # Añadir a la tabla existente
                index=False,         # No incluir el índice del DataFrame
                method='multi'       # Inserción en lotes para mayor rendimiento
            )
            logger.info(f"Insertados {rows_inserted} registros en tabla {table_name} para {dataset_type} batch {batch_number} usando to_sql")
            return rows_inserted
            
        except Exception as e:
            logger.warning(f"Error al usar to_sql: {str(e)}. Intentando método alternativo...")
            
            # Método 2: Si to_sql falla, insertar fila por fila con SQLAlchemy
            with engine.begin() as connection:
                rows_inserted = 0
                for _, row in df.iterrows():
                    # Filtrar valores None y crear un diccionario limpio
                    clean_row = {}
                    for column, value in row.items():
                        if pd.isna(value):
                            # Omitir valores nulos o establecer un valor predeterminado
                            # clean_row[column] = None  # Opción 1: Incluir como NULL
                            pass  # Opción 2: Omitir columna
                        else:
                            clean_row[column] = value
                    
                    if not clean_row:
                        logger.warning("Fila con todos los valores nulos, omitiendo...")
                        continue
                    
                    # Construir la consulta SQL con parámetros nombrados
                    columns_str = ', '.join(clean_row.keys())
                    placeholders_str = ', '.join([f':{col}' for col in clean_row.keys()])
                    sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders_str})"
                    
                    # Ejecutar la consulta con parámetros nombrados
                    connection.execute(text(sql), clean_row)
                    rows_inserted += 1
                
                logger.info(f"Insertados {rows_inserted} registros en tabla {table_name} para {dataset_type} batch {batch_number} usando método fila por fila")
                return rows_inserted
                
    except Exception as e:
        logger.error(f"Error procesando {dataset_type} batch {batch_number}: {str(e)}")
        raise
    
# Función principal para procesar todos los batches de un tipo de dataset
def process_dataset(dataset_type, **kwargs):
    """Procesa todos los batches de un tipo específico de dataset"""
    ti = kwargs['ti']
    
    # Obtener el número total de batches desde XCom
    total_batches_key = f'total_{dataset_type}_batches'
    total_batches = ti.xcom_pull(key=total_batches_key)
    
    if not total_batches:
        logger.error(f"No se pudo obtener el total de batches para {dataset_type}")
        return
        
    logger.info(f"Procesando {total_batches} batches para {dataset_type}")
    
    total_records = 0
    for batch_number in range(total_batches):
        records_inserted = fetch_and_store_batch(
            dataset_type=dataset_type,
            batch_number=batch_number,
            **kwargs
        )
        total_records += records_inserted
        
    logger.info(f"Completado procesamiento de {dataset_type}: {total_records} registros en total")
    return total_records

# Definición del DAG
with DAG(
    dag_id='fetch_and_store_diabetes_data',
    default_args=default_args,
    description='Obtiene datos de la API FastAPI y los almacena en MySQL',
    schedule_interval=None,  # Manual trigger
    catchup=False
) as dag:
    
    # Tarea para obtener información del dataset
    get_info_task = PythonOperator(
        task_id='get_dataset_info',
        python_callable=get_dataset_info,
        dag=dag,
    )
    
    # Grupo de tareas para datos de entrenamiento
    with TaskGroup(group_id='process_train_data') as process_train_group:
        # Obtener total de batches de entrenamiento
        get_train_batches_task = PythonOperator(
            task_id='get_total_train_batches',
            python_callable=get_total_batches,
            op_kwargs={'dataset_type': 'train'},
            dag=dag,
        )
        
        # Procesar batches de entrenamiento
        process_train_task = PythonOperator(
            task_id='process_train_batches',
            python_callable=process_dataset,
            op_kwargs={'dataset_type': 'train'},
            dag=dag,
        )
        
        # Definir dependencias dentro del grupo
        get_train_batches_task >> process_train_task
    
    # Grupo de tareas para datos de validación
    with TaskGroup(group_id='process_validation_data') as process_validation_group:
        # Obtener total de batches de validación
        get_validation_batches_task = PythonOperator(
            task_id='get_total_validation_batches',
            python_callable=get_total_batches,
            op_kwargs={'dataset_type': 'validation'},
            dag=dag,
        )
        
        # Procesar batches de validación
        process_validation_task = PythonOperator(
            task_id='process_validation_batches',
            python_callable=process_dataset,
            op_kwargs={'dataset_type': 'validation'},
            dag=dag,
        )
        
        # Definir dependencias dentro del grupo
        get_validation_batches_task >> process_validation_task
    
    # Grupo de tareas para datos de prueba
    with TaskGroup(group_id='process_test_data') as process_test_group:
        # Obtener total de batches de prueba
        get_test_batches_task = PythonOperator(
            task_id='get_total_test_batches',
            python_callable=get_total_batches,
            op_kwargs={'dataset_type': 'test'},
            dag=dag,
        )
        
        # Procesar batches de prueba
        process_test_task = PythonOperator(
            task_id='process_test_batches',
            python_callable=process_dataset,
            op_kwargs={'dataset_type': 'test'},
            dag=dag,
        )
        
        # Definir dependencias dentro del grupo
        get_test_batches_task >> process_test_task
    
    # Definir dependencias entre tareas y grupos
    get_info_task >> [process_train_group, process_validation_group, process_test_group]
