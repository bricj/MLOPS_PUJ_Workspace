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

# Definir rutas de almacenamiento dentro del volumen compartido
DATA_OUTPUT = "/opt/airflow/models/"  # Directorio donde guardaremos el modelo

# Función para entrenar el modelo
def train_model():

    # Conectar a MySQL
    mysql_hook = MySqlHook(mysql_conn_id="mysql_airflow_conn")  # Asegúrate de definir esta conexión en Airflow
    sql_query = "SELECT * FROM penguins_proc;"  
    df = mysql_hook.get_pandas_df(sql_query) # Cargar datos guardados
    
    y = df[['species']]
    X = df[['culmen_length_mm','culmen_depth_mm','flipper_length_mm','body_mass_g']]

    #dividir entre entrenamiento y validacion
    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=50, test_size=0.30)

    #entrenar modelo
    model = linear_model.LogisticRegression(multi_class='ovr', solver='liblinear')
    model.fit(X_train, y_train)

    #guardar modelo
    joblib.dump(model, DATA_OUTPUT + "model_logreg.pkl")


# Definir el DAG
default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
    "retries": 1,
}

#crear dag
with DAG(
    dag_id="train_model_penguins",
    default_args=default_args,
    schedule_interval=None,  # Se ejecuta manualmente
    catchup=False,
) as dag:

    #conectar funcion a dag
    train_model_task = PythonOperator(
        task_id="train_model",
        python_callable=train_model
    )

    train_model_task