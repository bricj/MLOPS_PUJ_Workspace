from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from airflow.providers.postgres.hooks.postgres import PostgresHook
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import mlflow
from sklearn.svm import SVC
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import train_test_split
import os
import boto3
from botocore.config import Config


IP_MLFLOW = "http://10.43.101.168:31485"

os.environ['MLFLOW_S3_ENDPOINT_URL'] = "http://10.43.101.168:30855"
os.environ['AWS_ACCESS_KEY_ID'] = "minioadmin"
os.environ['AWS_SECRET_ACCESS_KEY'] = "minioadmin123"

# Configuraci�n b�sica
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 5, 1),
    'email_on_failure': False,
    'retries': 1,
}

# Funci�n para realizar undersampling
def perform_undersampling_from_transformed(X_transformed, y, random_state=42, sampling_strategy=1.0):
    """
    Performs undersampling on already transformed data.
    """
    
    # Check if y is a pandas Series
    is_pandas_series = isinstance(y, pd.Series)
    if is_pandas_series:
        y_name = y.name
    
    # Get array representation
    y_array = y.values if is_pandas_series else y
    
    # Find indices of each class
    unique_classes = np.unique(y_array)
    class_indices = {}
    for cls in unique_classes:
        class_indices[cls] = np.where(y_array == cls)[0]
    
    # Display class distribution before resampling
    print("Class distribution before undersampling:")
    for cls, indices in class_indices.items():
        print(f"  Class {cls}: {len(indices)} samples")
    
    # Determine target count for majority class
    if len(unique_classes) != 2:
        raise ValueError("This function only supports binary classification problems")
    
    # Find majority and minority classes
    class_counts = [len(class_indices[cls]) for cls in unique_classes]
    majority_class_idx = np.argmax(class_counts)
    minority_class_idx = 1 - majority_class_idx
    
    majority_class = unique_classes[majority_class_idx]
    minority_class = unique_classes[minority_class_idx]
    
    minority_count = len(class_indices[minority_class])
    majority_count = len(class_indices[majority_class])
    
    # Calculate target sample count for majority class
    if sampling_strategy == 'auto' or sampling_strategy == 'majority':
        target_majority_count = minority_count
    elif isinstance(sampling_strategy, (int, float)):
        # sampling_strategy is ratio of minority:majority
        target_majority_count = int(minority_count / sampling_strategy)
    else:
        raise ValueError("sampling_strategy must be 'auto', 'majority', or a number")
    
    # Undersample majority class
    np.random.seed(random_state)
    selected_majority_indices = np.random.choice(
        class_indices[majority_class], 
        size=min(target_majority_count, majority_count), 
        replace=False
    )
    
    # Combine with minority class indices
    selected_indices = np.concatenate([selected_majority_indices, class_indices[minority_class]])
    
    # Get resampled data
    X_transformed_resampled = X_transformed[selected_indices]
    y_resampled = y_array[selected_indices]
    
    # Display class distribution after resampling
    unique_resampled, counts_resampled = np.unique(y_resampled, return_counts=True)
    print("Class distribution after undersampling:")
    for cls, count in zip(unique_resampled, counts_resampled):
        print(f"  Class {cls}: {count} samples")
    
    # Preserve pandas Series type if input was a Series
    if is_pandas_series:
        y_resampled = pd.Series(y_resampled, name=y_name)
    
    return X_transformed_resampled, y_resampled

# Funci�n para leer datos de entrenamiento
def train_data(**kwargs):
    """Lee los datos de entrenamiento y aplica undersampling."""

    # Test Minio connection
    s3 = boto3.client(
        's3',
        endpoint_url="http://10.43.101.168:30855",
        aws_access_key_id='minioadmin',
        aws_secret_access_key= 'minioadmin123'
    )

    try:
        buckets = s3.list_buckets()
        print("Connected to Minio. Buckets:", [b['Name'] for b in buckets['Buckets']])
    except Exception as e:
        print("Minio connection failed:", e)

    print(f"Version de mlflow: {mlflow.__version__}")
    print("Leyendo datos de la tabla diabetes_train_processed...")
    
    # try:
        # Conectar a MySQL
    postgres_hook = PostgresHook(postgres_conn_id="postgres_airflow_conn")  # Change to your actual connection ID
    
    # Leer tabla
    query = "SELECT * FROM diabetes_train_processed"
    df = postgres_hook.get_pandas_df(query)
    
    # Mostrar informaci�n b�sica
    print(f"Datos de entrenamiento:")
    print(f"- Forma: {df.shape}")
    print(f"- Columnas: {df.columns.tolist()}")
    print(f"- Primeras 5 filas:")
    print(df.head())
    
    # Separar caracter�sticas y variable objetivo
    X = df.drop('target', axis=1)
    y = df['target']
    
    # Mostrar distribuci�n de clases
    print("Distribuci�n de clases (entrenamiento):")
    print(y.value_counts())
    
    # # Aplicar undersampling
    # print("Aplicando undersampling al conjunto de entrenamiento...")
    # X_resampled, y_resampled = perform_undersampling_from_transformed(
    #     X.values, y, random_state=42, sampling_strategy='auto'
    # )

    X_resampled, _,y_resampled,_= train_test_split(X,y,random_state=420, train_size=1000)

    mlflow.set_tracking_uri(IP_MLFLOW)

    experiment_name = "minkube_mlflow_experiment"
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        mlflow.create_experiment(experiment_name)
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name="svm_artifacts") as run:
        params = {
        'C': [0.1, 1],
        'gamma': ['scale', 0.1],
    }

        # inicializar svm
        svm = SVC()

        # buscar hiperparametros mas optimos
        print('Iniciando optimizacion de parametros')
        # grid_search = GridSearchCV(svm, params, cv=2, scoring='accuracy', n_jobs=-1)
        # grid_search.fit(X_resampled, y_resampled)
        svm = SVC(C=1.0, kernel='rbf', gamma='scale')  # Ajusta los valores si lo deseas
        svm.fit(X_resampled, y_resampled)
        print('Optimizacion de parametros finalizada')

        mlflow.log_params(params)
        # mlflow.set_tag("column_names", ",".join(columns))
        mlflow.sklearn.log_model(
            sk_model=svm,
            artifact_path="svm",
            registered_model_name="svm-model"
        )

        # Se define nombre del modelo y version
        model_name = "svm-model"

        # Se lleva el modelo a ambiente de produccion
        client = mlflow.tracking.MlflowClient()

        latest_prod_version = client.get_latest_versions(
            name=model_name,
            stages=["Production"]
        )[-1].version
        
        # Crear una nueva versión del modelo
        # Transicionar a producción
        client.transition_model_version_stage(
            name=model_name,
            version=int(latest_prod_version)+1,
            stage="Production"
        )
        
        return "Entrenamiento completado"

# Funci�n para leer datos de validaci�n
def read_validation_data(**kwargs):
    """Lee los datos de validaci�n."""
    print("Leyendo datos de la tabla diabetes_validation_processed...")
    
    try:
        # Conectar a MySQL
        postgres_hook = PostgresHook(postgres_conn_id="postgres_airflow_conn")  # Change to your actual connection ID
        
        # Leer tabla
        query = "SELECT * FROM diabetes_validation_processed"
        df = postgres_hook.get_pandas_df(query)
        
        # Mostrar informaci�n b�sica
        print(f"Datos de validaci�n:")
        print(f"- Forma: {df.shape}")
        print(f"- Columnas: {df.columns.tolist()}")
        print(f"- Primeras 5 filas:")
        print(df.head())
        
        # Separar caracter�sticas y variable objetivo
        X = df.drop('target', axis=1)
        y = df['target']
        
        # Mostrar distribuci�n de clases
        print("Distribuci�n de clases (validaci�n):")
        print(y.value_counts())
        
        # Guardar datos
        import pickle
        data_dir = '/tmp/airflow/data'
        
        with open(f'{data_dir}/X_validation.pkl', 'wb') as f:
            pickle.dump(X.values, f)
        
        with open(f'{data_dir}/y_validation.pkl', 'wb') as f:
            pickle.dump(y, f)
        
        return "Procesamiento de datos de validaci�n completado"
    
    except Exception as e:
        print(f"Error al procesar los datos: {str(e)}")
        return f"Error: {str(e)}"

# Funci�n para leer datos de prueba
def read_test_data(**kwargs):
    """Lee los datos de prueba."""
    print("Leyendo datos de la tabla diabetes_test_processed...")
    
    try:
        # Conectar a MySQL
        postgres_hook = PostgresHook(postgres_conn_id="postgres_airflow_conn")  # Change to your actual connection ID
        
        # Leer tabla
        query = "SELECT * FROM diabetes_test_processed"
        df = postgres_hook.get_pandas_df(query)
        
        # Mostrar informaci�n b�sica
        print(f"Datos de prueba:")
        print(f"- Forma: {df.shape}")
        print(f"- Columnas: {df.columns.tolist()}")
        print(f"- Primeras 5 filas:")
        print(df.head())
        
        # Separar caracter�sticas y variable objetivo
        X = df.drop('target', axis=1)
        y = df['target']
        
        # Mostrar distribuci�n de clases
        print("Distribuci�n de clases (prueba):")
        print(y.value_counts())
        
        # Guardar datos
        import pickle
        data_dir = '/tmp/airflow/data'
        
        with open(f'{data_dir}/X_test.pkl', 'wb') as f:
            pickle.dump(X.values, f)
        
        with open(f'{data_dir}/y_test.pkl', 'wb') as f:
            pickle.dump(y, f)
        
        return "Procesamiento de datos de prueba completado"
    
    except Exception as e:
        print(f"Error al procesar los datos: {str(e)}")
        return f"Error: {str(e)}"

# Funci�n para entrenar el modelo
def train_model(**kwargs):
    """Entrena el modelo con los datos de entrenamiento balanceados."""
    try:
        # Cargar datos
        import pickle
        data_dir = '/tmp/airflow/data'
        
        with open(f'{data_dir}/X_train_resampled.pkl', 'rb') as f:
            X_train_resampled = pickle.load(f)
        
        with open(f'{data_dir}/y_train_resampled.pkl', 'rb') as f:
            y_train_resampled = pickle.load(f)
        
        # Entrenar modelo
        print("Entrenando modelo con datos balanceados...")
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train_resampled, y_train_resampled)
        
        # Guardar modelo
        import os
        model_dir = '/tmp/airflow/models'
        os.makedirs(model_dir, exist_ok=True)
        
        with open(f'{model_dir}/diabetes_model.pkl', 'wb') as f:
            pickle.dump(model, f)
        
        print(f"Modelo guardado en {model_dir}")
        
        return "Entrenamiento del modelo completado"
    
    except Exception as e:
        print(f"Error al entrenar el modelo: {str(e)}")
        return f"Error: {str(e)}"

# Funci�n para evaluar con datos de validaci�n
def evaluate_validation(**kwargs):
    """Eval�a el modelo con datos de validaci�n."""
    try:
        # Cargar modelo y datos
        import pickle
        data_dir = '/tmp/airflow/data'
        model_dir = '/tmp/airflow/models'
        
        with open(f'{model_dir}/diabetes_model.pkl', 'rb') as f:
            model = pickle.load(f)
        
        with open(f'{data_dir}/X_validation.pkl', 'rb') as f:
            X_validation = pickle.load(f)
        
        with open(f'{data_dir}/y_validation.pkl', 'rb') as f:
            y_validation = pickle.load(f)
        
        # Realizar predicciones
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
        
        y_pred = model.predict(X_validation)
        y_pred_proba = model.predict_proba(X_validation)[:, 1]
        
        # Calcular m�tricas
        results = {
            "accuracy": accuracy_score(y_validation, y_pred),
            "precision": precision_score(y_validation, y_pred, pos_label="YES"),
            "recall": recall_score(y_validation, y_pred, pos_label="YES"),
            "f1_score": f1_score(y_validation, y_pred, pos_label="YES"),
            "roc_auc": roc_auc_score(y_validation == "YES", y_pred_proba)
        }
        
        # Mostrar resultados
        print("Resultados en validaci�n:")
        for metric, value in results.items():
            print(f"- {metric}: {value:.4f}")
        
        # Guardar resultados
        with open(f'{data_dir}/validation_results.pkl', 'wb') as f:
            pickle.dump(results, f)
        
        return "Evaluaci�n en validaci�n completada"
    
    except Exception as e:
        print(f"Error en evaluaci�n: {str(e)}")
        return f"Error: {str(e)}"

# Funci�n para realizar inferencia en datos de prueba
def inference_test(**kwargs):
    """Realiza inferencia en datos de prueba."""
    try:
        # Cargar modelo y datos
        import pickle
        data_dir = '/tmp/airflow/data'
        model_dir = '/tmp/airflow/models'
        
        with open(f'{model_dir}/diabetes_model.pkl', 'rb') as f:
            model = pickle.load(f)
        
        with open(f'{data_dir}/X_test.pkl', 'rb') as f:
            X_test = pickle.load(f)
        
        with open(f'{data_dir}/y_test.pkl', 'rb') as f:
            y_test = pickle.load(f)
        
        # Realizar predicciones
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix, classification_report
        
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        # Calcular m�tricas
        results = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, pos_label="YES"),
            "recall": recall_score(y_test, y_pred, pos_label="YES"),
            "f1_score": f1_score(y_test, y_pred, pos_label="YES"),
            "roc_auc": roc_auc_score(y_test == "YES", y_pred_proba)
        }
        
        # Mostrar resultados
        print("Resultados en prueba:")
        for metric, value in results.items():
            print(f"- {metric}: {value:.4f}")
        
        # Mostrar matriz de confusi�n
        cm = confusion_matrix(y_test, y_pred)
        print("Matriz de confusi�n:")
        print(cm)
        
        # Mostrar informe de clasificaci�n
        print("Informe de clasificaci�n:")
        print(classification_report(y_test, y_pred))
        
        # Guardar resultados
        with open(f'{data_dir}/test_results.pkl', 'wb') as f:
            pickle.dump(results, f)
        
        return "Inferencia en prueba completada"
    
    except Exception as e:
        print(f"Error en inferencia: {str(e)}")
        return f"Error: {str(e)}"

# Funci�n para generar resumen
def generate_summary(**kwargs):
    """Genera un resumen del proceso completo."""
    try:
        # Cargar resultados
        import pickle
        data_dir = '/tmp/airflow/data'
        
        with open(f'{data_dir}/validation_results.pkl', 'rb') as f:
            validation_results = pickle.load(f)
        
        with open(f'{data_dir}/test_results.pkl', 'rb') as f:
            test_results = pickle.load(f)
        
        print("===== RESUMEN DEL PROCESO =====")
        print("1. Datos de entrenamiento balanceados")
        print("2. Modelo entrenado")
        print("3. Evaluaci�n e inferencia realizadas")
        
        print("\nComparaci�n de resultados:")
        print("| M�trica    | Validaci�n | Prueba    |")
        print("|------------|------------|-----------|")
        for metric in validation_results.keys():
            print(f"| {metric:<10} | {validation_results[metric]:.4f}     | {test_results[metric]:.4f}     |")
        
        print("\nProceso completado exitosamente")
        print("==============================")
        
        return "Resumen generado"
    
    except Exception as e:
        print(f"Error al generar resumen: {str(e)}")
        return f"Error: {str(e)}"

# Crear el DAG
with DAG(
    'diabetes_model_pipeline',
    default_args=default_args,
    description='Pipeline para datos de diabetes con balanceo e inferencia',
    schedule_interval=None,
) as dag:
    
    # Tareas
    train_model_task = PythonOperator(
        task_id='train_data',
        python_callable=train_data,
        provide_context=True,
    )
    
    # read_validation = PythonOperator(
    #     task_id='read_validation_data',
    #     python_callable=read_validation_data,
    #     provide_context=True,
    # )
    
    # read_test = PythonOperator(
    #     task_id='read_test_data',
    #     python_callable=read_test_data,
    #     provide_context=True,
    # )
    
    # train = PythonOperator(
    #     task_id='train_model',
    #     python_callable=train_model,
    #     provide_context=True,
    # )
    
    # evaluate = PythonOperator(
    #     task_id='evaluate_validation',
    #     python_callable=evaluate_validation,
    #     provide_context=True,
    # )
    
    # infer = PythonOperator(
    #     task_id='inference_test',
    #     python_callable=inference_test,
    #     provide_context=True,
    # )
    
    # summary = PythonOperator(
    #     task_id='generate_summary',
    #     python_callable=generate_summary,
    #     provide_context=True,
    # )
    
    # Definir dependencias
    train_model_task #>> read_validation >> read_test >> train >> evaluate >> infer >> summary