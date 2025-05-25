# """
# DAG para ingestión de datos desde API a PostgreSQL
# Procesa 10 grupos de datos de forma secuencial
# """

# from airflow import DAG
# from airflow.providers.postgres.hooks.postgres import PostgresHook
# from airflow.operators.python import PythonOperator
# from airflow.models import Connection
# from airflow.utils.db import provide_session
# from datetime import datetime
# from airflow.utils.dates import days_ago
# import requests
# import json
# import os

# # Configuración
# API_URL = "http://10.43.101.108/data"
# GROUPS = [3, 4, 5, 6, 7, 8, 9, 10, 1, 2]
# API_DAY = "Tuesday"
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
#     schedule_interval='@daily',
#     catchup=False,
#     tags=['api', 'ingestion', 'postgresql'],
# )

# @provide_session
# def create_postgres_connection(session=None):
#     """Crear conexión PostgreSQL usando variables de entorno"""
#     conn = session.query(Connection).filter(Connection.conn_id == POSTGRES_CONN_ID).first()
    
#     if not conn:
#         new_conn = Connection(
#             conn_id=POSTGRES_CONN_ID,
#             conn_type='postgres',
#             host=os.environ.get('RAW_DATA_DB_HOST', '10.43.101.166'),
#             port=int(os.environ.get('RAW_DATA_DB_PORT', '5433')),
#             schema=os.environ.get('RAW_DATA_DB_NAME', 'rawdata'),
#             login=os.environ.get('RAW_DATA_DB_USER', 'admin'),
#             password=os.environ.get('RAW_DATA_DB_PASSWORD', 'admin')
#         )
#         session.add(new_conn)
#         session.commit()
#         print("✅ Conexión PostgreSQL creada")
#     else:
#         print("✅ Conexión PostgreSQL ya existe")

# def validate_database():
#     """Validar conectividad a la base de datos"""
#     create_postgres_connection()
    
#     hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
#     result = hook.get_first("SELECT current_database();")
#     db_name = result[0]
#     print(f"✅ Conectado exitosamente a la base de datos: {db_name}")

# def cleanup_existing_tables():
#     """Eliminar tablas existentes si existen"""
#     hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
#     for group in GROUPS:
#         table_name = f"group_{group}_data"
#         sql = f"DROP TABLE IF EXISTS raw_data.{table_name} CASCADE;"
#         hook.run(sql)
#         print(f"🗑️ Tabla raw_data.{table_name} eliminada")
    
#     print("✅ Limpieza de tablas completada")

# def create_schema():
#     """Crear esquema raw_data si no existe"""
#     hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
#     hook.run("CREATE SCHEMA IF NOT EXISTS raw_data;")
#     print("✅ Esquema raw_data creado")

# def create_all_tables():
#     """Crear todas las tablas necesarias"""
#     hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
#     for group in GROUPS:
#         table_name = f"group_{group}_data"
#         sql = f"""
#             CREATE TABLE IF NOT EXISTS raw_data.{table_name} (
#                 brokered_by     TEXT,
#                 status          TEXT,
#                 price           NUMERIC,
#                 bed             INTEGER,
#                 bath            INTEGER,
#                 acre_lot        NUMERIC,
#                 street          TEXT,
#                 city            TEXT,
#                 state           TEXT,
#                 zip_code        TEXT,
#                 house_size      INTEGER,
#                 prev_sold_date  DATE,
#                 created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                 group_number    INTEGER DEFAULT {group}
#             );
#         """
#         hook.run(sql)
#         print(f"✅ Tabla raw_data.{table_name} creada")
    
#     print("✅ Todas las tablas creadas exitosamente")

# def fetch_and_store_group_data(group_number):
#     """Obtener datos de API y almacenar en PostgreSQL para un grupo específico"""
#     def _fetch_and_store():
#         try:
#             # Realizar petición a la API
#             params = {"group_number": group_number, "day": API_DAY}
#             print(f"🌐 Obteniendo datos del grupo {group_number}...")
            
#             response = requests.get(API_URL, params=params, timeout=60)
#             response.raise_for_status()
            
#             # Procesar respuesta JSON
#             json_data = response.json()
#             tabla = json_data.get("data", [])
            
#             if not tabla:
#                 print(f"⚠️ No hay datos en la respuesta para el grupo {group_number}")
#                 return
            
#             print(f"📊 Procesando {len(tabla)} registros para el grupo {group_number}...")
            
#             # Preparar datos para batch insert
#             hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
#             table_name = f"group_{group_number}_data"
            
#             # Definir columnas
#             target_fields = [
#                 'brokered_by', 'status', 'price', 'bed', 'bath', 'acre_lot',
#                 'street', 'city', 'state', 'zip_code', 'house_size', 'prev_sold_date'
#             ]
            
#             # Preparar todos los valores
#             rows_data = []
#             for record in tabla:
#                 row = (
#                     record.get('brokered_by'),
#                     record.get('status'),
#                     record.get('price'),
#                     record.get('bed'),
#                     record.get('bath'),
#                     record.get('acre_lot'),
#                     record.get('street'),
#                     record.get('city'),
#                     record.get('state'),
#                     record.get('zip_code'),
#                     record.get('house_size'),
#                     record.get('prev_sold_date')
#                 )
#                 rows_data.append(row)
            
#             # Batch insert por chunks para manejar grandes volúmenes
#             chunk_size = 5000  # Insertar de 5000 en 5000
#             total_inserted = 0
            
#             for i in range(0, len(rows_data), chunk_size):
#                 chunk = rows_data[i:i + chunk_size]
                
#                 # Usar insert_rows para batch insert eficiente
#                 hook.insert_rows(
#                     table=f"raw_data.{table_name}",
#                     rows=chunk,
#                     target_fields=target_fields,
#                     commit_every=0  # Commit solo al final de cada chunk
#                 )
                
#                 total_inserted += len(chunk)
#                 print(f"⏳ Insertados {total_inserted}/{len(rows_data)} registros...")
            
#             print(f"✅ Grupo {group_number}: {total_inserted} registros insertados exitosamente")
            
#         except Exception as e:
#             print(f"❌ Error para grupo {group_number}: {str(e)}")
#             print(f"⏭️ Continuando con el siguiente grupo...")
    
#     return _fetch_and_store

# def validate_results():
#     """Validar resultados finales"""
#     hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
#     total_records = 0
#     successful_groups = 0
    
#     for group in GROUPS:
#         table_name = f"group_{group}_data"
#         result = hook.get_first(f"SELECT COUNT(*) FROM raw_data.{table_name};")
#         count = result[0] if result else 0
#         total_records += count
        
#         if count > 0:
#             successful_groups += 1
#             print(f"📊 Grupo {group}: {count} registros")
#         else:
#             print(f"⚠️ Grupo {group}: Sin datos")
    
#     print(f"📈 Resumen final:")
#     print(f"   - Grupos exitosos: {successful_groups}/{len(GROUPS)}")
#     print(f"   - Total registros: {total_records}")

# # Crear tareas del DAG
# validate_db_task = PythonOperator(
#     task_id='validate_database',
#     python_callable=validate_database,
#     dag=dag,
# )

# cleanup_task = PythonOperator(
#     task_id='cleanup_existing_tables',
#     python_callable=cleanup_existing_tables,
#     dag=dag,
# )

# create_schema_task = PythonOperator(
#     task_id='create_schema',
#     python_callable=create_schema,
#     dag=dag,
# )

# create_tables_task = PythonOperator(
#     task_id='create_all_tables',
#     python_callable=create_all_tables,
#     dag=dag,
# )

# # Crear tareas secuenciales para cada grupo
# group_tasks = []
# for group in GROUPS:
#     task = PythonOperator(
#         task_id=f'fetch_group_{group}',
#         python_callable=fetch_and_store_group_data(group),
#         dag=dag,
#     )
#     group_tasks.append(task)

# validate_results_task = PythonOperator(
#     task_id='validate_results',
#     python_callable=validate_results,
#     dag=dag,
# )

# # Definir dependencias
# validate_db_task >> cleanup_task >> create_schema_task >> create_tables_task

# # Encadenar tareas de grupos secuencialmente
# current_task = create_tables_task
# for group_task in group_tasks:
#     current_task >> group_task
#     current_task = group_task

# # Finalizar con validación
# current_task >> validate_results_task

"""
DAG para ingestión de datos desde API a PostgreSQL
Procesa 10 grupos de datos de forma secuencial
"""

from airflow import DAG
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator
from airflow.models import Connection
from airflow.utils.db import provide_session
from datetime import datetime
from airflow.utils.dates import days_ago
import requests
import json
import os

# Configuración
API_URL = "http://10.43.101.108/data"
GROUPS = [3, 4, 5, 6, 7, 8, 9, 10, 1, 2]
API_DAY = "Tuesday"
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
    schedule_interval='@daily',
    catchup=False,
    tags=['api', 'ingestion', 'postgresql'],
)

@provide_session
def create_postgres_connection(session=None):
    """Crear conexión PostgreSQL usando variables de entorno"""
    conn = session.query(Connection).filter(Connection.conn_id == POSTGRES_CONN_ID).first()
    
    if not conn:
        new_conn = Connection(
            conn_id=POSTGRES_CONN_ID,
            conn_type='postgres',
            host=os.environ.get('RAW_DATA_DB_HOST', '10.43.101.166'),
            port=int(os.environ.get('RAW_DATA_DB_PORT', '5433')),
            schema=os.environ.get('RAW_DATA_DB_NAME', 'rawdata'),
            login=os.environ.get('RAW_DATA_DB_USER', 'admin'),
            password=os.environ.get('RAW_DATA_DB_PASSWORD', 'admin')
        )
        session.add(new_conn)
        session.commit()
        print("✅ Conexión PostgreSQL creada")
    else:
        print("✅ Conexión PostgreSQL ya existe")

def validate_database():
    """Validar conectividad a la base de datos"""
    create_postgres_connection()
    
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    result = hook.get_first("SELECT current_database();")
    db_name = result[0]
    print(f"✅ Conectado exitosamente a la base de datos: {db_name}")

def cleanup_existing_tables():
    """Eliminar tablas existentes si existen"""
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    for group in GROUPS:
        table_name = f"group_{group}_data"
        sql = f"DROP TABLE IF EXISTS raw_data.{table_name} CASCADE;"
        hook.run(sql)
        print(f"🗑️ Tabla raw_data.{table_name} eliminada")
    
    print("✅ Limpieza de tablas completada")

def create_schema():
    """Crear esquema raw_data si no existe"""
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    hook.run("CREATE SCHEMA IF NOT EXISTS raw_data;")
    print("✅ Esquema raw_data creado")

def create_all_tables():
    """Crear todas las tablas necesarias"""
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    for group in GROUPS:
        table_name = f"group_{group}_data"
        sql = f"""
            CREATE TABLE IF NOT EXISTS raw_data.{table_name} (
                brokered_by     TEXT,
                status          TEXT,
                price           NUMERIC,
                bed             INTEGER,
                bath            INTEGER,
                acre_lot        NUMERIC,
                street          TEXT,
                city            TEXT,
                state           TEXT,
                zip_code        TEXT,
                house_size      INTEGER,
                prev_sold_date  DATE,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                group_number    INTEGER DEFAULT {group}
            );
        """
        hook.run(sql)
        print(f"✅ Tabla raw_data.{table_name} creada")
    
    print("✅ Todas las tablas creadas exitosamente")

def fetch_and_store_group_data(group_number):
    """Obtener datos de API y almacenar en PostgreSQL para un grupo específico"""
    def _fetch_and_store():
        try:
            # Realizar petición a la API
            params = {"group_number": group_number, "day": API_DAY}
            print(f"🌐 Obteniendo datos del grupo {group_number}...")
            
            response = requests.get(API_URL, params=params, timeout=60)
            response.raise_for_status()
            
            # Procesar respuesta JSON
            json_data = response.json()
            tabla = json_data.get("data", [])
            
            if not tabla:
                print(f"⚠️ No hay datos en la respuesta para el grupo {group_number}")
                return
            
            print(f"📊 Procesando {len(tabla)} registros para el grupo {group_number}...")
            
            # Preparar datos para batch insert
            hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
            table_name = f"group_{group_number}_data"
            
            # Definir columnas
            target_fields = [
                'brokered_by', 'status', 'price', 'bed', 'bath', 'acre_lot',
                'street', 'city', 'state', 'zip_code', 'house_size', 'prev_sold_date'
            ]
            
            # Preparar todos los valores
            rows_data = []
            for record in tabla:
                row = (
                    record.get('brokered_by'),
                    record.get('status'),
                    record.get('price'),
                    record.get('bed'),
                    record.get('bath'),
                    record.get('acre_lot'),
                    record.get('street'),
                    record.get('city'),
                    record.get('state'),
                    record.get('zip_code'),
                    record.get('house_size'),
                    record.get('prev_sold_date')
                )
                rows_data.append(row)
            
            # Batch insert por chunks para manejar grandes volúmenes
            chunk_size = 5000  # Insertar de 5000 en 5000
            total_inserted = 0
            
            for i in range(0, len(rows_data), chunk_size):
                chunk = rows_data[i:i + chunk_size]
                
                # Usar insert_rows para batch insert eficiente
                hook.insert_rows(
                    table=f"raw_data.{table_name}",
                    rows=chunk,
                    target_fields=target_fields,
                    commit_every=0  # Commit solo al final de cada chunk
                )
                
                total_inserted += len(chunk)
                print(f"⏳ Insertados {total_inserted}/{len(rows_data)} registros...")
            
            print(f"✅ Grupo {group_number}: {total_inserted} registros insertados exitosamente")
            
        except Exception as e:
            print(f"❌ Error para grupo {group_number}: {str(e)}")
            print(f"⏭️ Continuando con el siguiente grupo...")
    
    return _fetch_and_store

def validate_results():
    """Validar resultados finales"""
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    total_records = 0
    successful_groups = 0
    
    for group in GROUPS:
        table_name = f"group_{group}_data"
        result = hook.get_first(f"SELECT COUNT(*) FROM raw_data.{table_name};")
        count = result[0] if result else 0
        total_records += count
        
        if count > 0:
            successful_groups += 1
            print(f"📊 Grupo {group}: {count} registros")
        else:
            print(f"⚠️ Grupo {group}: Sin datos")
    
    print(f"📈 Resumen final:")
    print(f"   - Grupos exitosos: {successful_groups}/{len(GROUPS)}")
    print(f"   - Total registros: {total_records}")

# Crear tareas del DAG
validate_db_task = PythonOperator(
    task_id='validate_database',
    python_callable=validate_database,
    dag=dag,
)

cleanup_task = PythonOperator(
    task_id='cleanup_existing_tables',
    python_callable=cleanup_existing_tables,
    dag=dag,
)

create_schema_task = PythonOperator(
    task_id='create_schema',
    python_callable=create_schema,
    dag=dag,
)

create_tables_task = PythonOperator(
    task_id='create_all_tables',
    python_callable=create_all_tables,
    dag=dag,
)

# Crear tareas secuenciales para cada grupo
group_tasks = []
for group in GROUPS:
    task = PythonOperator(
        task_id=f'fetch_group_{group}',
        python_callable=fetch_and_store_group_data(group),
        dag=dag,
    )
    group_tasks.append(task)

validate_results_task = PythonOperator(
    task_id='validate_results',
    python_callable=validate_results,
    dag=dag,
)

# Definir dependencias
validate_db_task >> cleanup_task >> create_schema_task >> create_tables_task

# Encadenar tareas de grupos secuencialmente
current_task = create_tables_task
for group_task in group_tasks:
    current_task >> group_task
    current_task = group_task

# Finalizar con validación
current_task >> validate_results_task