# from airflow import DAG
# from airflow.providers.postgres.hooks.postgres import PostgresHook
# from airflow.operators.python import PythonOperator
# from airflow.models import Connection
# from airflow.utils.db import provide_session
# from datetime import datetime
# from airflow.utils.dates import days_ago
# import requests
# import os

# # Configuración
# API_URL = "http://10.43.101.108/data"
# POSTGRES_CONN_ID = "postgres_raw_data"

# default_args = {
#     'owner': 'mlops-team',
#     'depends_on_past': False,
#     'start_date': days_ago(1),
#     'email_on_failure': False,
#     'retries': 1,
# }

# dag = DAG(
#     'api_data_ingestion',
#     default_args=default_args,
#     description='Ingestión de datos desde API a PostgreSQL',
#     schedule_interval=None,
#     catchup=False,
#     tags=['api', 'ingestion', 'postgresql'],
# )

# @provide_session
# def setup_connection(session=None):
#     """Configurar conexión PostgreSQL"""
#     if not session.query(Connection).filter(Connection.conn_id == POSTGRES_CONN_ID).first():
#         conn = Connection(
#             conn_id=POSTGRES_CONN_ID,
#             conn_type='postgres',
#             host=os.environ.get('RAW_DATA_DB_HOST', '10.43.101.166'),
#             port=int(os.environ.get('RAW_DATA_DB_PORT', '5433')),
#             schema=os.environ.get('RAW_DATA_DB_NAME', 'rawdata'),
#             login=os.environ.get('RAW_DATA_DB_USER', 'admin'),
#             password=os.environ.get('RAW_DATA_DB_PASSWORD', 'admin')
#         )
#         session.add(conn)
#         session.commit()

# def setup_database(**context):
#     """Configurar base de datos y tabla"""
#     setup_connection()
#     hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
#     # Obtener número de batch
#     batch_number = context['dag_run'].conf.get('batch_number', 1) if context['dag_run'].conf else 1
#     table_name = f"api_data_batch_{batch_number}"
    
#     # Limpiar y crear
#     hook.run(f"DROP TABLE IF EXISTS raw_data.{table_name} CASCADE;")
#     hook.run("CREATE SCHEMA IF NOT EXISTS raw_data;")
#     hook.run(f"""
#         CREATE TABLE raw_data.{table_name} (
#             brokered_by TEXT, status TEXT, price NUMERIC, bed INTEGER,
#             bath INTEGER, acre_lot NUMERIC, street TEXT, city TEXT,
#             state TEXT, zip_code TEXT, house_size INTEGER, 
#             prev_sold_date DATE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         );
#     """)
#     print(f"✅ Base de datos configurada para batch {batch_number}")

# def load_data(**context):
#     """Cargar datos de API a PostgreSQL"""
#     start_time = datetime.now()
    
#     # Obtener número de batch
#     batch_number = context['dag_run'].conf.get('batch_number', 1) if context['dag_run'].conf else 1
#     table_name = f"api_data_batch_{batch_number}"
    
#     # Obtener datos
#     response = requests.get(API_URL, params={"group_number": 3, "day": "Tuesday"})
#     response.raise_for_status()
#     data = response.json().get("data", [])
    
#     if not data:
#         print("⚠️ No hay datos")
#         return
    
#     # Preparar datos
#     hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
#     fields = ['brokered_by', 'status', 'price', 'bed', 'bath', 'acre_lot',
#               'street', 'city', 'state', 'zip_code', 'house_size', 'prev_sold_date']
    
#     rows = [(record.get(field) for field in fields) for record in data]
    
#     # Insertar en chunks
#     chunk_size = 5000
#     total = len(rows)
    
#     for i in range(0, total, chunk_size):
#         chunk = rows[i:i + chunk_size]
#         hook.insert_rows(f"raw_data.{table_name}", chunk, fields, commit_every=0)
#         print(f"⏳ {min(i + chunk_size, total):,}/{total:,} registros")
    
#     # Métricas
#     execution_time = (datetime.now() - start_time).total_seconds()
#     size_mb = (total * len(fields) * 50) / (1024 * 1024)
    
#     print(f"📊 MÉTRICAS:")
#     print(f"   📈 Filas: {total:,}")
#     print(f"   📋 Columnas: {len(fields)}")
#     print(f"   💾 Tamaño estimado: {size_mb:.2f} MB")
#     print(f"   ⏱️ Tiempo: {execution_time:.2f} segundos")
#     print(f"   🚀 Velocidad: {total/execution_time:,.0f} filas/seg")

# def validate_data(**context):
#     """Validar datos cargados"""
#     batch_number = context['dag_run'].conf.get('batch_number', 1) if context['dag_run'].conf else 1
#     table_name = f"api_data_batch_{batch_number}"
    
#     hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
#     count = hook.get_first(f"SELECT COUNT(*) FROM raw_data.{table_name};")[0]
#     print(f"✅ {count:,} registros cargados en raw_data.{table_name}")

# # Tareas
# setup_db_task = PythonOperator(task_id='setup_database', python_callable=setup_database, dag=dag)
# load_data_task = PythonOperator(task_id='load_data', python_callable=load_data, dag=dag)
# validate_task = PythonOperator(task_id='validate_data', python_callable=validate_data, dag=dag)

# # Flujo
# setup_db_task >> load_data_task >> validate_task

from airflow import DAG
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator
from airflow.models import Connection
from airflow.utils.db import provide_session
from datetime import datetime
from airflow.utils.dates import days_ago
import requests
import os

# Configuración
API_URL = "http://10.43.101.108/data"
POSTGRES_CONN_ID = "postgres_raw_data"

default_args = {
    'owner': 'mlops-team',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'retries': 1,
}

dag = DAG(
    'api_data_ingestion',
    default_args=default_args,
    description='Ingestión de datos desde API a PostgreSQL',
    schedule_interval=None,
    catchup=False,
    tags=['api', 'ingestion', 'postgresql'],
)

@provide_session
def setup_connection(session=None):
    """Configurar conexión PostgreSQL"""
    if not session.query(Connection).filter(Connection.conn_id == POSTGRES_CONN_ID).first():
        conn = Connection(
            conn_id=POSTGRES_CONN_ID,
            conn_type='postgres',
            host=os.environ.get('RAW_DATA_DB_HOST', '10.43.101.166'),
            port=int(os.environ.get('RAW_DATA_DB_PORT', '5433')),
            schema=os.environ.get('RAW_DATA_DB_NAME', 'rawdata'),
            login=os.environ.get('RAW_DATA_DB_USER', 'admin'),
            password=os.environ.get('RAW_DATA_DB_PASSWORD', 'admin')
        )
        session.add(conn)
        session.commit()

def setup_database(**context):
    """Configurar base de datos y tabla"""
    setup_connection()
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    # Obtener número de batch
    batch_number = context['dag_run'].conf.get('batch_number', 1) if context['dag_run'].conf else 1
    table_name = f"api_data_batch_{batch_number}"
    
    # Limpiar y crear
    hook.run(f"DROP TABLE IF EXISTS raw_data.{table_name} CASCADE;")
    hook.run("CREATE SCHEMA IF NOT EXISTS raw_data;")
    hook.run(f"""
        CREATE TABLE raw_data.{table_name} (
            brokered_by TEXT, status TEXT, price NUMERIC, bed INTEGER,
            bath INTEGER, acre_lot NUMERIC, street TEXT, city TEXT,
            state TEXT, zip_code TEXT, house_size INTEGER, 
            prev_sold_date DATE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print(f"✅ Base de datos configurada para batch {batch_number}")

def load_data(**context):
    """Cargar datos de API a PostgreSQL"""
    start_time = datetime.now()
    
    # Obtener número de batch
    batch_number = context['dag_run'].conf.get('batch_number', 1) if context['dag_run'].conf else 1
    table_name = f"api_data_batch_{batch_number}"
    
    # Obtener datos
    response = requests.get(API_URL, params={"group_number": 3, "day": "Tuesday"})
    response.raise_for_status()
    data = response.json().get("data", [])
    
    if not data:
        print("⚠️ No hay datos")
        return
    
    # Preparar datos
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    fields = ['brokered_by', 'status', 'price', 'bed', 'bath', 'acre_lot',
              'street', 'city', 'state', 'zip_code', 'house_size', 'prev_sold_date']
    
    rows = [(record.get(field) for field in fields) for record in data]
    
    # Insertar en chunks
    chunk_size = 5000
    total = len(rows)
    
    for i in range(0, total, chunk_size):
        chunk = rows[i:i + chunk_size]
        hook.insert_rows(f"raw_data.{table_name}", chunk, fields, commit_every=0)
        print(f"⏳ {min(i + chunk_size, total):,}/{total:,} registros")
    
    # Métricas
    execution_time = (datetime.now() - start_time).total_seconds()
    size_mb = (total * len(fields) * 50) / (1024 * 1024)
    
    print(f" MÉTRICAS:")
    print(f"    Filas: {total:,}")
    print(f"    Columnas: {len(fields)}")
    print(f"    Tamaño estimado: {size_mb:.2f} MB")
    print(f"   ⏱️ Tiempo: {execution_time:.2f} segundos")
    print(f"    Velocidad: {total/execution_time:,.0f} filas/seg")

def validate_data(**context):
    """Validar datos cargados y mostrar estadísticas descriptivas"""
    batch_number = context['dag_run'].conf.get('batch_number', 1) if context['dag_run'].conf else 1
    table_name = f"api_data_batch_{batch_number}"
    
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    # Contar registros totales
    count = hook.get_first(f"SELECT COUNT(*) FROM raw_data.{table_name};")[0]
    print(f"✅ {count:,} registros cargados en raw_data.{table_name}")
    
    # Definir variables numéricas para análisis estadístico
    numeric_columns = ['price', 'bed', 'bath', 'acre_lot', 'house_size']
    
    print(f"\n📊 ESTADÍSTICAS DESCRIPTIVAS:")
    print("=" * 80)
    
    for column in numeric_columns:
        try:
            # Query para obtener estadísticas descriptivas
            stats_query = f"""
                SELECT 
                    '{column}' as variable,
                    COUNT({column}) as count_valid,
                    COUNT(*) - COUNT({column}) as count_null,
                    MIN({column}) as minimum,
                    MAX({column}) as maximum,
                    AVG({column}) as mean,
                    STDDEV_POP({column}) as std_deviation,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {column}) as median
                FROM raw_data.{table_name}
                WHERE {column} IS NOT NULL;
            """
            
            result = hook.get_first(stats_query)
            
            if result and result[1] > 0:  # Si hay datos válidos
                variable, count_valid, count_null, minimum, maximum, mean, std_dev, median = result
                
                print(f"📈 {variable.upper()}:")
                print(f"    Registros válidos: {count_valid:,}")
                print(f"    Registros nulos: {count_null:,}")
                print(f"    Mínimo: {minimum:,.2f}" if minimum is not None else "    Mínimo: N/A")
                print(f"    Máximo: {maximum:,.2f}" if maximum is not None else "    Máximo: N/A")
                print(f"    Promedio: {mean:.2f}" if mean is not None else "    Promedio: N/A")
                print(f"    Desv. Estándar: {std_dev:.2f}" if std_dev is not None else "    Desv. Estándar: N/A")
                print(f"    Mediana: {median:.2f}" if median is not None else "    Mediana: N/A")
                print("-" * 40)
            else:
                print(f"⚠️ {column.upper()}: Sin datos válidos para análisis")
                print("-" * 40)
                
        except Exception as e:
            print(f"❌ Error al calcular estadísticas para {column}: {str(e)}")
            print("-" * 40)
    
    # Estadísticas adicionales de calidad de datos
    print(f"\n🔍 CALIDAD DE DATOS:")
    print("=" * 50)
    
    # Conteo de valores únicos en columnas categóricas
    categorical_columns = ['brokered_by', 'status', 'city', 'state']
    
    for column in categorical_columns:
        try:
            unique_count_query = f"""
                SELECT COUNT(DISTINCT {column}) as unique_values,
                       COUNT({column}) as non_null_count
                FROM raw_data.{table_name};
            """
            unique_result = hook.get_first(unique_count_query)
            
            if unique_result:
                unique_values, non_null_count = unique_result
                print(f"📋 {column.upper()}:")
                print(f"    Valores únicos: {unique_values:,}")
                print(f"    Valores no nulos: {non_null_count:,}")
        except Exception as e:
            print(f"❌ Error al analizar {column}: {str(e)}")
    
    # Resumen final
    print(f"\n🎯 RESUMEN FINAL:")
    print("=" * 40)
    print(f"✅ Dataset cargado exitosamente")
    print(f"📊 Total de registros: {count:,}")
    print(f"🗂️ Variables numéricas analizadas: {len(numeric_columns)}")
    print(f"📑 Variables categóricas analizadas: {len(categorical_columns)}")
    print(f"⏰ Validación completada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Tareas
setup_db_task = PythonOperator(task_id='setup_database', python_callable=setup_database, dag=dag)
load_data_task = PythonOperator(task_id='load_data', python_callable=load_data, dag=dag)
validate_task = PythonOperator(task_id='validate_data', python_callable=validate_data, dag=dag)

# Flujo
setup_db_task >> load_data_task >> validate_task