"""
DAG para leer las tablas de datos de diabetes (train, validation, test)
y registrar la cantidad de filas y columnas leídas.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from datetime import datetime, timedelta
import pandas as pd
import logging

# Configuración de logging
logger = logging.getLogger(__name__)

# Argumentos por defecto para el DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 5, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

# Función para leer datos de una tabla específica
def read_diabetes_table(table_type, **kwargs):
    """
    Lee una tabla de diabetes y registra información sobre filas y columnas.
    
    Args:
        table_type: Tipo de tabla a leer ('train', 'validation' o 'test')
        
    Returns:
        None (los resultados se registran en los logs)
    """
    table_name = f"diabetes_{table_type}"
    logger.info(f"Iniciando lectura de tabla {table_name}...")
    
    try:
        # Conectar a MySQL usando la conexión configurada en Airflow
        mysql_hook = MySqlHook(mysql_conn_id="mysql_diabetes_conn")
        
        # Leer la tabla completa en un DataFrame
        query = f"SELECT * FROM {table_name}"
        df = mysql_hook.get_pandas_df(query)
        
        # Registrar información sobre los datos leídos
        num_rows = len(df)
        num_cols = len(df.columns)
        
        logger.info(f"✅ Tabla {table_name} leída exitosamente:")
        logger.info(f"   - Filas: {num_rows}")
        logger.info(f"   - Columnas: {num_cols}")
        logger.info(f"   - Nombres de columnas: {', '.join(df.columns.tolist())}")
        
        # Registrar información sobre valores nulos
        null_counts = df.isnull().sum().sum()
        logger.info(f"   - Total de valores nulos: {null_counts}")
        
        # Guardar resultados en XCom para uso posterior si es necesario
        kwargs['ti'].xcom_push(key=f'{table_type}_rows', value=num_rows)
        kwargs['ti'].xcom_push(key=f'{table_type}_columns', value=num_cols)
        
        # Retornar el DataFrame (aunque no lo usaremos directamente)
        return df
    
    except Exception as e:
        logger.error(f"❌ Error al leer tabla {table_name}: {str(e)}")
        raise

# Función para resumir todos los resultados
def summarize_results(**kwargs):
    """
    Resume los resultados de todas las lecturas de tablas.
    """
    ti = kwargs['ti']
    
    # Obtener información de cada tabla
    tables = ['train', 'validation', 'test']
    results = {}
    
    for table in tables:
        rows = ti.xcom_pull(key=f'{table}_rows', task_ids=f'read_{table}_data')
        cols = ti.xcom_pull(key=f'{table}_columns', task_ids=f'read_{table}_data')
        
        results[table] = {
            'rows': rows,
            'columns': cols
        }
    
    # Registrar resumen
    logger.info("=== RESUMEN DE LECTURA DE DATOS DE DIABETES ===")
    for table, info in results.items():
        if info['rows'] is not None and info['columns'] is not None:
            logger.info(f"Tabla diabetes_{table}: {info['rows']} filas, {info['columns']} columnas")
        else:
            logger.info(f"Tabla diabetes_{table}: Error en la lectura")
    
    # Verificar si todas las tablas se leyeron correctamente
    all_success = all(info['rows'] is not None for info in results.values())
    
    if all_success:
        logger.info("✅ Todas las tablas se leyeron correctamente")
    else:
        logger.error("❌ Una o más tablas no se pudieron leer correctamente")
    
    return results

# Definición del DAG
with DAG(
    'read_diabetes_tables',
    default_args=default_args,
    description='Lee las tablas de datos de diabetes y registra la cantidad de filas y columnas',
    schedule_interval=None,  # Ejecución manual
) as dag:
    
    # Tarea para leer datos de entrenamiento
    read_train = PythonOperator(
        task_id='read_train_data',
        python_callable=read_diabetes_table,
        op_kwargs={'table_type': 'train'},
        provide_context=True,
    )
    
    # Tarea para leer datos de validación
    read_validation = PythonOperator(
        task_id='read_validation_data',
        python_callable=read_diabetes_table,
        op_kwargs={'table_type': 'validation'},
        provide_context=True,
    )
    
    # Tarea para leer datos de prueba
    read_test = PythonOperator(
        task_id='read_test_data',
        python_callable=read_diabetes_table,
        op_kwargs={'table_type': 'test'},
        provide_context=True,
    )
    
    # Tarea para resumir resultados
    summarize = PythonOperator(
        task_id='summarize_results',
        python_callable=summarize_results,
        provide_context=True,
    )
    
    # Definir orden de ejecución
    [read_train, read_validation, read_test] >> summarize