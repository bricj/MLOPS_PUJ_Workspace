from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn import linear_model
from sklearn.metrics import classification_report
import joblib
from airflow.utils.dates import days_ago
from airflow.providers.mysql.hooks.mysql import MySqlHook
import mlflow
from sklearn.model_selection import train_test_split
from sklearn.model_selection import GridSearchCV
import os
import boto3
from sklearn.svm import SVC



# Definir rutas de almacenamiento dentro del volumen compartido
DATA_OUTPUT = "/opt/airflow/models/"  # Directorio donde guardaremos el modelo

# Función para entrenar el modelo
def train_model():

    print("MLflow Version:", mlflow.__version__)

    # Establecer credenciales de acceso a Minio.
    # Indicar IP donde se ha desplegado Minio

    ip_minio = "http://minio:9000"
    user_minio = 'admin'
    password_minio = 'supersecret'
    ip_mlflow = "http://mlflow:5000"

    os.environ['MLFLOW_S3_ENDPOINT_URL'] = ip_minio
    os.environ['AWS_ACCESS_KEY_ID'] = user_minio
    os.environ['AWS_SECRET_ACCESS_KEY'] = password_minio

    # Conectar a MySQL
    mysql_hook = MySqlHook(mysql_conn_id="mysql_airflow_conn")  # Asegúrate de definir esta conexión en Airflow
    sql_query = "SELECT * FROM suelos_proc LIMIT 1000;"  
    df = mysql_hook.get_pandas_df(sql_query) # Cargar datos guardados
    columns = df.columns

    # Particion datos de entrenamiento y evaluacion
    y = df['Cover_Type']
    X = df[['Elevation', 'Aspect', 'Slope', 'Horizontal_Distance_To_Hydrology',
       'Vertical_Distance_To_Hydrology', 'Horizontal_Distance_To_Roadways',
       'Hillshade_9am', 'Hillshade_Noon', 'Hillshade_3pm',
       'Horizontal_Distance_To_Fire_Points', 'Wilderness_Area','Wilderness_Area',
       'Soil_Type']]

    # Dividir entre entrenamiento y validacion
    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=50, test_size=0.30)

    ### Definir funcion mlflow

    # Se define la IP donde se ha desplegado mlflow y el nombre del experimento
    mlflow.set_tracking_uri(ip_mlflow)
    experiment_name = "mlflow_tracking_examples_4"
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        mlflow.create_experiment(experiment_name)
    mlflow.set_experiment(experiment_name)

    # Se definen parametros del experimento
    with mlflow.start_run(run_name="svm_artifacts") as run:
        params = {
        'C': [0.1, 1],
        'gamma': ['scale', 0.1],
    }

        # inicializar svm
        svm = SVC()

        # buscar hiperparametros mas optimos
        grid_search = GridSearchCV(svm, params, cv=5, scoring='accuracy', n_jobs=-1)
        grid_search.fit(X_train, y_train)

        mlflow.log_params(params)
        mlflow.set_tag("column_names", ",".join(columns))
        mlflow.sklearn.log_model(
        sk_model=grid_search,
        artifact_path="svm",
            registered_model_name="svm-model"
        )

        # Se define nombre del modelo y version
        model_name = "svm-model"
        model_version = 4

        # Se lleva el modelo a ambiente de produccion
        client = mlflow.tracking.MlflowClient()
        #registered_model = client.create_registered_model(model_name)
        

        # Crear una nueva versión del modelo
        model_uri = f"runs:/{run.info.run_id}/svm"
        #model_version = client.create_model_version(model_name, model_uri, run.info.run_id)

        # Transicionar a producción
        client.transition_model_version_stage(
            name=model_name,
            version=model_version,
            stage="Production"
        )

    # #guardar modelo
    # # Configuración de MinIO
    # minio_endpoint = ip_minio  # Ajusta si está en otro servidor
    # access_key = user_minio
    # secret_key = password_minio
    # bucket_name = "mlflows3"
    # object_key = "artifacts/1/e5b9a57d50534be9bd5ae97f5390da60/artifacts/best_estimator/model.pkl"
    # local_file_path = "models/model.pkl"

    # # Crear cliente MinIO
    # s3_client = boto3.client(
    #     "s3",
    #     endpoint_url=minio_endpoint,
    #     aws_access_key_id=access_key,
    #     aws_secret_access_key=secret_key
    # )

    # # Descargar el archivo
    # s3_client.download_file(bucket_name, object_key, local_file_path)


# Definir el DAG
default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
    "retries": 1,
}

#crear dag
with DAG(
    dag_id="train_model",
    default_args=default_args,
    description='Ejecuta experimentos de modelo svm en mlflow',
    schedule_interval=None,  # Se ejecuta manualmente
    catchup=False,
) as dag:

    #conectar funcion a dag
    train_model_task = PythonOperator(
        task_id="train_model",
        python_callable=train_model
    )

    train_model_task