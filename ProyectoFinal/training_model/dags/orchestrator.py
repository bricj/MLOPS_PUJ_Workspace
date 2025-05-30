# from airflow import DAG
# from airflow.providers.postgres.hooks.postgres import PostgresHook
# from airflow.operators.python import PythonOperator
# from airflow.operators.trigger_dagrun import TriggerDagRunOperator
# from airflow.sensors.external_task import ExternalTaskSensor
# from airflow.models import Connection
# from airflow.utils.db import provide_session
# from datetime import datetime
# from airflow.utils.dates import days_ago
# import requests
# import os

# # Configuración
# RESTART_URL = "http://10.43.101.108/restart_data_generation"
# DAG1_ID = "api_data_ingestion"
# DAG2_ID = "data_processing"
# POSTGRES_CONN_ID = "postgres_raw_data"

# default_args = {
#     'owner': 'mlops-team',
#     'depends_on_past': False,
#     'start_date': days_ago(1),
#     'email_on_failure': False,
#     'retries': 1,
# }

# dag = DAG(
#     'mlops_pipeline_orchestrator',
#     default_args=default_args,
#     description='Orquestador del pipeline MLOps - Procesa todos los batches disponibles',
#     schedule_interval='@daily',
#     catchup=False,
#     tags=['orchestrator', 'mlops', 'pipeline'],
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

# def restart_api():
#     """Reiniciar endpoint al inicio del pipeline"""
#     response = requests.get(RESTART_URL, params={"group_number": 3, "day": "Tuesday"})
#     response.raise_for_status()
#     print("✅ Endpoint reiniciado - Pipeline iniciado")

# def setup_database():
#     """Configurar base de datos"""
#     setup_connection()
#     hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
#     hook.run("CREATE SCHEMA IF NOT EXISTS raw_data;")
#     print("✅ Base de datos configurada")

# def execute_batch_pipeline(**context):
#     """Ejecutar pipeline completo para todos los batches disponibles"""
#     from airflow.api.common.trigger_dag import trigger_dag
#     from airflow.utils.state import State
#     from airflow.models import DagRun
#     import time
    
#     batch_number = 1
#     successful_batches = 0
#     total_records = 0
#     start_time = datetime.now()
    
#     print(f"🚀 Iniciando procesamiento de batches...")
    
#     while True:
#         try:
#             print(f"\n📦 PROCESANDO BATCH {batch_number}")
            
#             # Ejecutar DAG1 para este batch
#             print(f"🔄 Ejecutando DAG1 para batch {batch_number}...")
#             dag1_run = trigger_dag(
#                 dag_id=DAG1_ID,
#                 conf={'batch_number': batch_number},
#                 execution_date=None,
#                 replace_microseconds=False
#             )
            
#             # Esperar que DAG1 complete
#             dag1_completed = False
#             timeout_counter = 0
#             max_timeout = 1800  # 30 minutos
            
#             while not dag1_completed and timeout_counter < max_timeout:
#                 time.sleep(30)
#                 timeout_counter += 30
                
#                 dag_run = DagRun.find(dag_id=DAG1_ID, execution_date=dag1_run.execution_date)[0]
                
#                 if dag_run.state == State.SUCCESS:
#                     dag1_completed = True
#                     print(f"✅ DAG1 completado exitosamente para batch {batch_number}")
#                 elif dag_run.state == State.FAILED:
#                     # Verificar si es error 422 (fin de batches)
#                     if "422" in str(dag_run.log) or batch_number > 1:
#                         print(f"🏁 Fin de batches detectado en batch {batch_number}")
#                         break
#                     else:
#                         raise Exception(f"DAG1 falló para batch {batch_number}")
            
#             if timeout_counter >= max_timeout:
#                 raise Exception(f"DAG1 timeout para batch {batch_number}")
            
#             if not dag1_completed:
#                 break
            
#             # Ejecutar DAG2 para este batch
#             print(f"🔄 Ejecutando DAG2 para batch {batch_number}...")
#             dag2_run = trigger_dag(
#                 dag_id=DAG2_ID,
#                 conf={'batch_number': batch_number},
#                 execution_date=None,
#                 replace_microseconds=False
#             )
            
#             # Esperar que DAG2 complete
#             dag2_completed = False
#             timeout_counter = 0
            
#             while not dag2_completed and timeout_counter < max_timeout:
#                 time.sleep(30)
#                 timeout_counter += 30
                
#                 dag_run = DagRun.find(dag_id=DAG2_ID, execution_date=dag2_run.execution_date)[0]
                
#                 if dag_run.state == State.SUCCESS:
#                     dag2_completed = True
#                     print(f"✅ DAG2 completado exitosamente para batch {batch_number}")
#                 elif dag_run.state == State.FAILED:
#                     raise Exception(f"DAG2 falló para batch {batch_number}")
            
#             if timeout_counter >= max_timeout:
#                 raise Exception(f"DAG2 timeout para batch {batch_number}")
            
#             # Obtener métricas del batch procesado
#             hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
#             raw_table = f"api_data_batch_{batch_number}"
            
#             try:
#                 count = hook.get_first(f"SELECT COUNT(*) FROM raw_data.{raw_table};")[0]
#                 total_records += count
#                 print(f"📊 Batch {batch_number}: {count:,} registros procesados")
#             except:
#                 count = 0
            
#             successful_batches += 1
#             batch_number += 1
            
#         except requests.exceptions.HTTPError as e:
#             if "422" in str(e):
#                 print(f"🏁 Todos los batches procesados. Error 422 indica fin de datos.")
#                 break
#             else:
#                 print(f"❌ Error HTTP: {e}")
#                 raise
#         except Exception as e:
#             if "422" in str(e) or "fin de batches" in str(e).lower():
#                 print(f"🏁 Procesamiento de batches completado")
#                 break
#             else:
#                 print(f"❌ Error procesando batch {batch_number}: {str(e)}")
#                 raise
    
#     # Métricas finales
#     total_time = (datetime.now() - start_time).total_seconds()
#     print(f"\n📊 RESUMEN FINAL DEL PIPELINE:")
#     print(f"   🎯 Batches procesados exitosamente: {successful_batches}")
#     print(f"   📈 Total registros procesados: {total_records:,}")
#     print(f"   ⏱️ Tiempo total: {total_time:.2f} segundos")
#     if total_records > 0:
#         print(f"   🚀 Velocidad promedio: {total_records/total_time:,.0f} registros/seg")
#     print(f"   📋 Tablas creadas:")
#     for i in range(1, successful_batches + 1):
#         print(f"      - raw_data.api_data_batch_{i}")
#         print(f"      - raw_data.api_data_batch_{i}_processed")

# def validate_pipeline():
#     """Validar resultados del pipeline completo"""
#     hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
#     # Encontrar todas las tablas batch
#     tables_sql = """
#         SELECT table_name 
#         FROM information_schema.tables 
#         WHERE table_schema = 'raw_data' 
#         AND table_name LIKE 'api_data_batch_%'
#         ORDER BY table_name;
#     """
    
#     tables = hook.get_records(tables_sql)
#     raw_tables = [t[0] for t in tables if not t[0].endswith('_processed')]
#     processed_tables = [t[0] for t in tables if t[0].endswith('_processed')]
    
#     print(f"📊 VALIDACIÓN DEL PIPELINE:")
#     print(f"   📋 Tablas raw encontradas: {len(raw_tables)}")
#     print(f"   📋 Tablas processed encontradas: {len(processed_tables)}")
    
#     total_raw_records = 0
#     total_processed_records = 0
    
#     for table in raw_tables:
#         count = hook.get_first(f"SELECT COUNT(*) FROM raw_data.{table};")[0]
#         total_raw_records += count
#         print(f"   ✅ {table}: {count:,} registros")
    
#     for table in processed_tables:
#         count = hook.get_first(f"SELECT COUNT(*) FROM raw_data.{table};")[0]
#         total_processed_records += count
#         print(f"   ✅ {table}: {count:,} registros")
    
#     print(f"\n📈 TOTALES:")
#     print(f"   Raw: {total_raw_records:,} registros")
#     print(f"   Processed: {total_processed_records:,} registros")

# # Tareas del DAG Orquestador
# setup_db_task = PythonOperator(task_id='setup_database', python_callable=setup_database, dag=dag)
# restart_api_task = PythonOperator(task_id='restart_api', python_callable=restart_api, dag=dag)
# execute_pipeline_task = PythonOperator(task_id='execute_batch_pipeline', python_callable=execute_batch_pipeline, dag=dag)
# validate_pipeline_task = PythonOperator(task_id='validate_pipeline', python_callable=validate_pipeline, dag=dag)

# # Flujo del orquestador
# setup_db_task >> restart_api_task >> execute_pipeline_task >> validate_pipeline_task

from airflow import DAG
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.models import Connection
from airflow.utils.db import provide_session
from datetime import datetime
from airflow.utils.dates import days_ago
import requests
import os

# Configuración
RESTART_URL = "http://10.43.101.108/restart_data_generation"
DAG1_ID = "api_data_ingestion"
DAG2_ID = "data_processing"
DAG3_ID = "model_training"  # ← Nuevo DAG3
POSTGRES_CONN_ID = "postgres_raw_data"

default_args = {
    'owner': 'mlops-team',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'retries': 1,
}

dag = DAG(
    'mlops_pipeline_orchestrator',
    default_args=default_args,
    description='Orquestador del pipeline MLOps - Procesa todos los batches DAG1→DAG2→DAG3',
    schedule_interval='@daily',
    catchup=False,
    tags=['orchestrator', 'mlops', 'pipeline'],
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

def restart_api():
    """Reiniciar endpoint al inicio del pipeline"""
    response = requests.get(RESTART_URL, params={"group_number": 3, "day": "Tuesday"})
    response.raise_for_status()
    print("✅ Endpoint reiniciado - Pipeline iniciado")

def setup_database():
    """Configurar base de datos"""
    setup_connection()
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    hook.run("CREATE SCHEMA IF NOT EXISTS raw_data;")
    print("✅ Base de datos configurada")

def execute_batch_pipeline(**context):
    """Ejecutar pipeline completo para todos los batches disponibles: DAG1→DAG2→DAG3"""
    from airflow.api.common.trigger_dag import trigger_dag
    from airflow.utils.state import State
    from airflow.models import DagRun
    import time
    
    batch_number = 1
    successful_batches = 0
    total_records = 0
    start_time = datetime.now()
    
    print(f"🚀 Iniciando procesamiento de batches...")
    
    while True:
        try:
            print(f"\n🔄 PROCESANDO BATCH {batch_number}")
            
            # Ejecutar DAG1 para este batch
            print(f"📊 Ejecutando DAG1 para batch {batch_number}...")
            dag1_run = trigger_dag(
                dag_id=DAG1_ID,
                conf={'batch_number': batch_number},
                execution_date=None,
                replace_microseconds=False
            )
            
            # Esperar que DAG1 complete
            dag1_completed = False
            timeout_counter = 0
            max_timeout = 1800  # 30 minutos
            
            while not dag1_completed and timeout_counter < max_timeout:
                time.sleep(30)
                timeout_counter += 30
                
                dag_run = DagRun.find(dag_id=DAG1_ID, execution_date=dag1_run.execution_date)[0]
                
                if dag_run.state == State.SUCCESS:
                    dag1_completed = True
                    print(f"✅ DAG1 completado exitosamente para batch {batch_number}")
                elif dag_run.state == State.FAILED:
                    # Verificar si es error 422 (fin de batches)
                    if "422" in str(dag_run.log) or batch_number > 1:
                        print(f"🏁 Fin de batches detectado en batch {batch_number}")
                        break
                    else:
                        raise Exception(f"DAG1 falló para batch {batch_number}")
            
            if timeout_counter >= max_timeout:
                raise Exception(f"DAG1 timeout para batch {batch_number}")
            
            if not dag1_completed:
                break
            
            # Ejecutar DAG2 para este batch
            print(f"⚙️ Ejecutando DAG2 para batch {batch_number}...")
            dag2_run = trigger_dag(
                dag_id=DAG2_ID,
                conf={'batch_number': batch_number},
                execution_date=None,
                replace_microseconds=False
            )
            
            # Esperar que DAG2 complete
            dag2_completed = False
            timeout_counter = 0
            
            while not dag2_completed and timeout_counter < max_timeout:
                time.sleep(30)
                timeout_counter += 30
                
                dag_run = DagRun.find(dag_id=DAG2_ID, execution_date=dag2_run.execution_date)[0]
                
                if dag_run.state == State.SUCCESS:
                    dag2_completed = True
                    print(f"✅ DAG2 completado exitosamente para batch {batch_number}")
                elif dag_run.state == State.FAILED:
                    raise Exception(f"DAG2 falló para batch {batch_number}")
            
            if timeout_counter >= max_timeout:
                raise Exception(f"DAG2 timeout para batch {batch_number}")
            
            # Ejecutar DAG3 para este batch
            print(f"🤖 Ejecutando DAG3 para batch {batch_number}...")
            dag3_run = trigger_dag(
                dag_id=DAG3_ID,
                conf={'batch_number': batch_number},
                execution_date=None,
                replace_microseconds=False
            )
            
            # Esperar que DAG3 complete
            dag3_completed = False
            timeout_counter = 0
            
            while not dag3_completed and timeout_counter < max_timeout:
                time.sleep(30)
                timeout_counter += 30
                
                dag_run = DagRun.find(dag_id=DAG3_ID, execution_date=dag3_run.execution_date)[0]
                
                if dag_run.state == State.SUCCESS:
                    dag3_completed = True
                    print(f"✅ DAG3 completado exitosamente para batch {batch_number}")
                elif dag_run.state == State.FAILED:
                    raise Exception(f"DAG3 falló para batch {batch_number}")
            
            if timeout_counter >= max_timeout:
                raise Exception(f"DAG3 timeout para batch {batch_number}")
            
            # Obtener métricas del batch procesado
            hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
            raw_table = f"api_data_batch_{batch_number}"
            
            try:
                count = hook.get_first(f"SELECT COUNT(*) FROM raw_data.{raw_table};")[0]
                total_records += count
                print(f"📊 Batch {batch_number}: {count:,} registros procesados")
            except:
                count = 0
            
            successful_batches += 1
            batch_number += 1
            
        except requests.exceptions.HTTPError as e:
            if "422" in str(e):
                print(f"🏁 Todos los batches procesados. Error 422 indica fin de datos.")
                break
            else:
                print(f"❌ Error HTTP: {e}")
                raise
        except Exception as e:
            if "422" in str(e) or "fin de batches" in str(e).lower():
                print(f"🏁 Procesamiento de batches completado")
                break
            else:
                print(f"❌ Error procesando batch {batch_number}: {str(e)}")
                raise
    
    # Métricas finales
    total_time = (datetime.now() - start_time).total_seconds()
    print(f"\n📊 RESUMEN FINAL DEL PIPELINE:")
    print(f"   📊 Batches procesados exitosamente: {successful_batches}")
    print(f"   📊 Total registros procesados: {total_records:,}")
    print(f"   ⏱️ Tiempo total: {total_time:.2f} segundos")
    if total_records > 0:
        print(f"   🚀 Velocidad promedio: {total_records/total_time:,.0f} registros/seg")
    print(f"   📊 Tablas creadas:")
    for i in range(1, successful_batches + 1):
        print(f"     - raw_data.api_data_batch_{i}")
        print(f"     - raw_data.api_data_batch_{i}_processed")
        print(f"     - MLflow: lasso_training_batch_{i}")

def validate_pipeline():
    """Validar resultados del pipeline completo"""
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    # Encontrar todas las tablas batch
    tables_sql = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'raw_data' 
        AND table_name LIKE 'api_data_batch_%'
        ORDER BY table_name;
    """
    
    tables = hook.get_records(tables_sql)
    raw_tables = [t[0] for t in tables if not t[0].endswith('_processed')]
    processed_tables = [t[0] for t in tables if t[0].endswith('_processed')]
    
    print(f"🔍 VALIDACIÓN DEL PIPELINE:")
    print(f"   📊 Tablas raw encontradas: {len(raw_tables)}")
    print(f"   📊 Tablas processed encontradas: {len(processed_tables)}")
    
    total_raw_records = 0
    total_processed_records = 0
    
    for table in raw_tables:
        count = hook.get_first(f"SELECT COUNT(*) FROM raw_data.{table};")[0]
        total_raw_records += count
        print(f"   ✅ {table}: {count:,} registros")
    
    for table in processed_tables:
        count = hook.get_first(f"SELECT COUNT(*) FROM raw_data.{table};")[0]
        total_processed_records += count
        print(f"   ✅ {table}: {count:,} registros")
    
    print(f"\n📊 TOTALES:")
    print(f"   📊 Raw: {total_raw_records:,} registros")
    print(f"   📊 Processed: {total_processed_records:,} registros")
    print(f"   🤖 Modelos: {len(processed_tables)} experimentos en MLflow")

# Tareas del DAG Orquestador
setup_db_task = PythonOperator(task_id='setup_database', python_callable=setup_database, dag=dag)
restart_api_task = PythonOperator(task_id='restart_api', python_callable=restart_api, dag=dag)
execute_pipeline_task = PythonOperator(task_id='execute_batch_pipeline', python_callable=execute_batch_pipeline, dag=dag)
validate_pipeline_task = PythonOperator(task_id='validate_pipeline', python_callable=validate_pipeline, dag=dag)

# Flujo del orquestador
setup_db_task >> restart_api_task >> execute_pipeline_task >> validate_pipeline_task