from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn import linear_model
from sklearn.metrics import classification_report
import joblib
from airflow.utils.dates import days_ago

# Definir rutas de almacenamiento dentro del volumen compartido
DATA_OUTPUT = "/opt/airflow/models/"  # Directorio donde guardaremos el modelo

# Función para entrenar el modelo
def train_model():
    df = pd.read_csv(DATA_OUTPUT + "penguins_transformed.csv")
    
    y = df[['species']]
    X = df[['island', 'sex', 'culmen_length_mm','culmen_depth_mm','flipper_length_mm']]

    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=50, test_size=0.30)

    model = linear_model.LogisticRegression(multi_class='ovr', solver='liblinear')
    model.fit(X_train, y_train)

    joblib.dump(model, DATA_OUTPUT + "model_logreg.pkl")
    #joblib.dump(model, ".models/" + "model_logreg.pkl")

    y_pred = model.predict(X_test)
    target_names = ['Adelie', 'Gentoo', 'Chinstrap']
    print(classification_report(y_test, y_pred, target_names=target_names))


# Definir el DAG
default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
    "retries": 1,
}

with DAG(
    dag_id="train_model_penguins",
    default_args=default_args,
    schedule_interval=None,  # Se ejecuta manualmente
    catchup=False,
) as dag:

    train_model_task = PythonOperator(
        task_id="train_model",
        python_callable=train_model
    )

    # Definir la secuencia de tareas
    train_model_task