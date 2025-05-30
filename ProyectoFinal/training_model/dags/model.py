from airflow import DAG
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator
from airflow.models import Connection
from airflow.utils.db import provide_session
from datetime import datetime
from airflow.utils.dates import days_ago
import pandas as pd
import os
import mlflow
from sklearn.linear_model import Lasso
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# Configuración
DAG_ID = "model_training"
POSTGRES_CONN_ID = "postgres_raw_data"

# Configuración MLflow y MinIO
IP_MLFLOW = "http://10.43.101.168:30500"
os.environ['MLFLOW_S3_ENDPOINT_URL'] = "http://10.43.101.168:30900"
os.environ['AWS_ACCESS_KEY_ID'] = "minioadmin"
os.environ['AWS_SECRET_ACCESS_KEY'] = "minioadmin123"

default_args = {
    'owner': 'mlops-team',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'retries': 1,
}

dag = DAG(
    DAG_ID,
    default_args=default_args,
    description='DAG3 - Entrenamiento de modelo Lasso por batch',
    schedule_interval=None,  # Ejecutado solo por orquestador
    catchup=False,
    tags=['model-training', 'mlops', 'lasso'],
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

def setup_mlflow():
    """Configurar MLflow"""
    mlflow.set_tracking_uri(IP_MLFLOW)
    client = mlflow.tracking.MlflowClient()
    
    experiment_name = "argocd_experiment"
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        mlflow.create_experiment(experiment_name)
        experiment = client.get_experiment_by_name(experiment_name)
    
    mlflow.set_experiment(experiment_name)
    return client

def promote_to_production(client, model_name, current_mse, current_run_id):
    """Promover modelo a producción si es mejor que el anterior"""
    try:
        production_models = client.get_latest_versions(model_name, stages=["Production"])
        
        if not production_models:
            # No hay modelo en producción, promover este
            latest_versions = client.search_model_versions(f"name='{model_name}'")
            latest_version = max(int(m.version) for m in latest_versions)
            
            client.transition_model_version_stage(
                name=model_name,
                version=latest_version,
                stage="Production"
            )
            print(f"🚀 Primer modelo promovido a producción - Versión: {latest_version}")
            return "Production"
        
        # Comparar con modelo en producción
        prod_model = production_models[0]
        prod_run = client.get_run(prod_model.run_id)
        prod_mse = prod_run.data.metrics.get('mse', float('inf'))
        
        print(f"📊 Comparando MSE - Producción: {prod_mse:.6f} vs Nuevo: {current_mse:.6f}")
        
        # Obtener última versión
        latest_versions = client.search_model_versions(f"name='{model_name}'")
        latest_version = max(int(m.version) for m in latest_versions)
        
        if current_mse < prod_mse:
            # Archivar modelo anterior
            client.transition_model_version_stage(
                name=model_name,
                version=prod_model.version,
                stage="Archived"
            )
            
            # Promover nuevo modelo
            client.transition_model_version_stage(
                name=model_name,
                version=latest_version,
                stage="Production"
            )
            
            improvement = ((prod_mse - current_mse) / prod_mse * 100)
            print(f"🚀 Nuevo modelo promovido a producción - Mejora: {improvement:.2f}%")
            return "Production"
        else:
            # Mantener en staging
            client.transition_model_version_stage(
                name=model_name,
                version=latest_version,
                stage="Staging"
            )
            print(f"📋 Modelo en staging - No supera al actual")
            return "Staging"
            
    except Exception as e:
        print(f"❌ Error en promoción: {str(e)}")
        return "None"

def execute_model_training(**context):
    """Ejecutar pipeline completo de entrenamiento de modelo Lasso para regresión de precios"""
    # Obtener parámetros del orquestador
    batch_number = context['dag_run'].conf.get('batch_number', 1)
    
    print(f"🤖 ENTRENAMIENTO MODELO LASSO - BATCH {batch_number}")
    print("=" * 50)
    
    try:
        # Setup conexión DB
        setup_connection()
        hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        
        # 1. VALIDAR Y CARGAR DATOS PROCESADOS DEL DAG2
        print(f"📊 Cargando datos procesados del DAG2 - batch {batch_number}...")
        processed_table = f"api_data_batch_{batch_number}_processed"
        
        # Verificar existencia de tabla procesada por DAG2
        table_exists = hook.get_first(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'raw_data' 
                AND table_name = '{processed_table}'
            );
        """)[0]
        
        if not table_exists:
            raise Exception(f"Tabla raw_data.{processed_table} no existe - DAG2 debe ejecutarse primero")
        
        # Contar registros
        row_count = hook.get_first(f"SELECT COUNT(*) FROM raw_data.{processed_table};")[0]
        
        if row_count == 0:
            raise Exception(f"Tabla raw_data.{processed_table} está vacía - DAG2 no procesó datos")
        
        # Cargar TODOS los datos procesados dinámicamente (sin asumir estructura)
        df = hook.get_pandas_df(f"""
            SELECT * FROM raw_data.{processed_table}
            WHERE id IS NOT NULL
            ORDER BY created_at;
        """)
        
        # Limpiar metadatos automáticamente (preservar solo datos del DAG2)
        metadata_columns = ['id', 'created_at']
        df = df.drop(columns=[col for col in metadata_columns if col in df.columns], errors='ignore')
        
        original_columns = list(df.columns)
        col_count = len(df.columns)
        
        print(f"✅ Datos procesados cargados (estructura dinámica):")
        print(f"   📊 Filas: {row_count:,}")
        print(f"   📈 Columnas totales: {col_count}")
        print(f"   🏗️ Provienen de: DAG2 feature engineering")
        print(f"   📋 Columnas detectadas: {original_columns[:10]}{'...' if len(original_columns) > 10 else ''}")
        
        # 2. DETECTAR AUTOMÁTICAMENTE COLUMNA TARGET
        target_candidates = ['target', 'price', 'y', 'label', 'outcome']
        target_column = None
        
        for candidate in target_candidates:
            if candidate in df.columns:
                target_column = candidate
                break
        
        if target_column is None:
            # Intentar detectar por tipo de datos o posición
            numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
            if len(numeric_cols) > 0:
                # Usar última columna numérica como target (convención común)
                target_column = numeric_cols[-1]
                print(f"⚠️ Target autodetectado: '{target_column}' (última columna numérica)")
            else:
                raise Exception("No se pudo detectar columna target - DAG2 debe generar variable objetivo")
        else:
            print(f"🎯 Target detectado: '{target_column}'")
        
        # Separar features dinámicamente
        feature_cols = [col for col in df.columns if col != target_column]
        
        print(f"   📊 Features disponibles: {len(feature_cols)}")
        print(f"   🎯 Variable target: {target_column}")
        
        # Análisis exploratorio dinámico de features
        if len(feature_cols) > 0:
            # Detectar tipos de features automáticamente
            binary_features = []
            continuous_features = []
            
            for col in feature_cols:
                unique_vals = df[col].nunique()
                if unique_vals == 2 and set(df[col].unique()).issubset({0, 1, True, False}):
                    binary_features.append(col)
                elif df[col].dtype in ['float64', 'int64']:
                    continuous_features.append(col)
            
            print(f"   🔢 Features continuas detectadas: {len(continuous_features)}")
            print(f"   🏷️ Features binarias/categóricas: {len(binary_features)}")
            
            # Log sample de features para debugging
            if len(feature_cols) <= 20:
                print(f"   📝 Todas las features: {feature_cols}")
            else:
                print(f"   📝 Primeras 20 features: {feature_cols[:20]}")
        else:
            raise Exception("No se detectaron features - DAG2 debe generar columnas de características")
        
        # 3. CONFIGURAR MLFLOW
        print(f"⚙️ Configurando MLflow...")
        client = setup_mlflow()
        
        # 4. ENTRENAR MODELO CON ESTRUCTURA DINÁMICA
        print(f"🔥 Iniciando entrenamiento con estructura dinámica...")
        
        with mlflow.start_run(run_name=f"lasso_training_batch_{batch_number}") as run:
            
            # Preparar datos dinámicamente
            X = df[feature_cols].copy()  # Todas las features detectadas
            y = df[target_column].copy()  # Target detectado automáticamente
            
            print(f"   📊 X shape: {X.shape}")
            print(f"   🎯 y shape: {y.shape}")
            print(f"   📈 Target stats: min={y.min():.2f}, max={y.max():.2f}, mean={y.mean():.2f}")
            
            # Validar datos antes del entrenamiento
            if X.isnull().any().any():
                print("⚠️ Detectados valores NaN en features - aplicando fillna con mediana")
                X = X.fillna(X.median(numeric_only=True))
            
            if y.isnull().any():
                print("⚠️ Detectados valores NaN en target - eliminando filas")
                valid_indices = ~y.isnull()
                X = X[valid_indices]
                y = y[valid_indices]
                print(f"   📊 Datos después de limpieza: {X.shape[0]} filas")
            
            # División train/test
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Entrenar modelo Lasso
            start_time = datetime.now()
            lasso_model = Lasso(alpha=1.0, random_state=42)
            lasso_model.fit(X_train, y_train)
            training_time = (datetime.now() - start_time).total_seconds()
            
            # Predicciones y métricas
            y_pred = lasso_model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            # 5. LOGGING EN MLFLOW (ESTRUCTURA DINÁMICA)
            print(f"📋 Registrando experimento en MLflow...")
            
            # Log parámetros del modelo
            mlflow.log_param("model_type", "Lasso")
            mlflow.log_param("alpha", 1.0)
            mlflow.log_param("problem_type", "regression")
            mlflow.log_param("target_column", target_column)
            
            # Log parámetros de datos (estructura dinámica)
            mlflow.log_param("batch_number", batch_number)
            mlflow.log_param("data_rows", row_count)
            mlflow.log_param("total_features", len(feature_cols))
            mlflow.log_param("feature_names", str(feature_cols)[:500])  # Truncar para evitar límites
            mlflow.log_param("continuous_features", len(continuous_features))
            mlflow.log_param("binary_features", len(binary_features))
            mlflow.log_param("data_source", "DAG2_processed_dynamic")
            mlflow.log_param("target_detection", "automatic")
            
            # Log estadísticas del target
            mlflow.log_param("target_min", float(y.min()))
            mlflow.log_param("target_max", float(y.max()))
            mlflow.log_param("target_mean", float(y.mean()))
            mlflow.log_param("target_std", float(y.std()))
            
            # Log parámetros de entrenamiento
            mlflow.log_param("train_size", len(X_train))
            mlflow.log_param("test_size", len(X_test))
            mlflow.log_param("test_split_ratio", 0.2)
            mlflow.log_param("training_time_seconds", training_time)
            
            # Log metadatos del pipeline
            mlflow.log_param("airflow_dag_run_id", context['dag_run'].run_id)
            mlflow.log_param("data_table", f"raw_data.{processed_table}")
            mlflow.log_param("upstream_dag", "data_processing")
            mlflow.log_param("feature_detection", "dynamic")
            
            # Log métricas
            mlflow.log_metric("mse", mse)
            mlflow.log_metric("mae", mae)
            mlflow.log_metric("r2_score", r2)
            
            # 6. REGISTRAR MODELO
            print(f"💾 Registrando modelo...")
            model_name = "lasso-regressor"
            mlflow.sklearn.log_model(
                sk_model=lasso_model,
                artifact_path="lasso",
                registered_model_name=model_name
            )
            
            # 7. PROMOCIÓN DE MODELO
            print(f"🚀 Evaluando promoción...")
            stage = promote_to_production(client, model_name, mse, run.info.run_id)
            
            # Log información de promoción
            mlflow.log_param("model_stage", stage)
            
            # 8. RESULTADOS FINALES (ESTRUCTURA DINÁMICA)
            print(f"\n📊 RESULTADOS MODELO DINÁMICO - BATCH {batch_number}:")
            print(f"   🎯 Target detectado: '{target_column}'")
            print(f"   📈 MSE: {mse:.6f}")
            print(f"   📉 MAE: {mae:.6f}")
            print(f"   📊 R² Score: {r2:.6f}")
            print(f"   ⏱️ Tiempo entrenamiento: {training_time:.2f}s")
            print(f"   🔢 Features procesadas: {len(feature_cols)} (dinámico)")
            print(f"   📊 Features continuas: {len(continuous_features)}")
            print(f"   🏷️ Features binarias: {len(binary_features)}")
            print(f"   🏷️ Modelo: {model_name}")
            print(f"   🎯 Estado: {stage}")
            print(f"   🆔 MLflow Run ID: {run.info.run_id}")
            print(f"   🌐 MLflow UI: {IP_MLFLOW}")
            print(f"   🔄 Pipeline: DAG1→DAG2→DAG3 (adaptativo)")
            
            return {
                'batch_number': batch_number,
                'model_name': model_name,
                'target_column': target_column,
                'total_features': len(feature_cols),
                'continuous_features': len(continuous_features),
                'binary_features': len(binary_features),
                'mse': mse,
                'mae': mae,
                'r2_score': r2,
                'model_stage': stage,
                'run_id': run.info.run_id,
                'records_processed': row_count,
                'training_time': training_time,
                'feature_detection': 'dynamic'
            }
            
    except Exception as e:
        print(f"❌ Error en entrenamiento batch {batch_number}: {str(e)}")
        raise

# Task del DAG
model_training_task = PythonOperator(
    task_id='execute_model_training',
    python_callable=execute_model_training,
    dag=dag
)