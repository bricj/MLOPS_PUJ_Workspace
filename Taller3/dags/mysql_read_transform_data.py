from airflow import DAG
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.operators.python import PythonOperator
from datetime import datetime
import pandas as pd
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn import linear_model
from sklearn.metrics import classification_report
import os
import joblib

# Definir rutas de almacenamiento dentro del volumen compartido
DATA_OUTPUT = "/opt/airflow/models/"  # Directorio donde guardaremos el modelo

# Función para cargar datos desde MySQL
def load_data_from_mysql():
    mysql_hook = MySqlHook(mysql_conn_id="mysql_airflow_conn")  # Conexión en Airflow
    sql_query = "SELECT * FROM penguins;"  
    df = mysql_hook.get_pandas_df(sql_query)

    # Guardar copia local del DataFrame para debugging
    os.makedirs(DATA_OUTPUT, exist_ok=True)
    df.to_csv(DATA_OUTPUT + "penguins.csv", index=False)
    
    return df

# Función para limpiar los datos
def clean_data():
    df = pd.read_csv(DATA_OUTPUT + "penguins.csv")  # Cargar datos guardados
    features = ['species','island','culmen_length_mm','culmen_depth_mm',
                'flipper_length_mm','body_mass_g','sex']
    
    df = df[features].dropna()
    df = df[df['sex'] != '.']  # Eliminar datos inválidos
    df.to_csv(DATA_OUTPUT + "penguins_clean.csv", index=False)

# Función para transformar variables
def transform_data():
    df = pd.read_csv(DATA_OUTPUT + "penguins_clean.csv")
    
    variables_categoricas = ['species','island', 'sex']
    variables_continuas = ['culmen_length_mm','culmen_depth_mm','flipper_length_mm']
    
    le = LabelEncoder()
    for var in variables_categoricas:
        df[var] = le.fit_transform(df[var])
    
    scaler = MinMaxScaler()
    df[variables_continuas] = scaler.fit_transform(df[variables_continuas])
    
    df.to_csv(DATA_OUTPUT + "penguins_transformed.csv", index=False)

# Función para entrenar el modelo
def train_model():
    df = pd.read_csv(DATA_OUTPUT + "penguins_transformed.csv")
    
    y = df[['species']]
    X = df[['island', 'sex', 'culmen_length_mm','culmen_depth_mm','flipper_length_mm']]

    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=50, test_size=0.30)

    model = linear_model.LogisticRegression(multi_class='ovr', solver='liblinear')
    model.fit(X_train, y_train)

    joblib.dump(model, DATA_OUTPUT + "model_logreg.pkl")

    y_pred = model.predict(X_test)
    target_names = ['Adelie', 'Gentoo', 'Chinstrap']
    print(classification_report(y_test, y_pred, target_names=target_names))


# Definir el DAG
default_args = {
    "owner": "airflow",
    "start_date": datetime(2024, 3, 5),
    "retries": 1,
}

with DAG(
    dag_id="entrenar_modelo_penguins",
    default_args=default_args,
    schedule_interval=None,  # Se ejecuta manualmente
    catchup=False,
) as dag:

    load_data = PythonOperator(
        task_id="load_data",
        python_callable=load_data_from_mysql
    )

    clean_data_task = PythonOperator(
        task_id="clean_data",
        python_callable=clean_data
    )

    transform_data_task = PythonOperator(
        task_id="transform_data",
        python_callable=transform_data
    )

    train_model_task = PythonOperator(
        task_id="train_model",
        python_callable=train_model
    )

    # Definir la secuencia de tareas
    load_data >> clean_data_task >> transform_data_task >> train_model_task
