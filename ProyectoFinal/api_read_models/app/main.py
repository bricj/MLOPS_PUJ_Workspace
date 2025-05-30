import os
os.environ['MLFLOW_S3_ENDPOINT_URL'] = "http://10.43.101.168:30900" #minio
os.environ['AWS_ACCESS_KEY_ID'] = 'minioadmin'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'minioadmin123'

import joblib
import mlflow.models
import mlflow.tracking
import mlflow.sklearn
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
import logging
import mlflow
import requests
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import create_engine, Table, Column, Integer, String, Float, MetaData
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

# Ruta donde están los modelos dentro del contenedor Docker
MODEL_DIR = "http://10.43.101.168:30500" #Mlflow
mlflow.set_tracking_uri(MODEL_DIR)
client = mlflow.tracking.MlflowClient(tracking_uri=MODEL_DIR) 


# URL de la base de datos de logs
DATABASE_URL = "postgresql://airflow:airflowpass@10.43.101.168:30543/airflow"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData()

# Definir la tabla (puedes ajustar tipos y nombres)
predictions_table = Table(
    "predictions", metadata,
    Column("id", Integer, primary_key=True, index=True, autoincrement=True),
    Column("model_name", String),
    Column("city", String),
    Column("state", String),
    Column("brokered_by", String),
    Column("price", Float),
    Column("bed", Float),
    Column("bath", Float),
    Column("acre_lot", Float),
    Column("street", String),
    Column("zip_code", String),
    Column("house_size", Float),
    Column("prev_sold_date",String)
)

# Crear la tabla si no existe
metadata.create_all(bind=engine)

app = FastAPI()

class PredictionInput(BaseModel):
    city: str
    state: str
    brokered_by: str
    bed: float
    bath: float
    acre_lot: float
    street: str
    zip_code: str
    house_size: float
    prev_sold_date: str




# Configuracion del logger
logging.basicConfig(
    filename='./logs/mi_app.log',
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

def load_model(model_name: str):
    """Carga un modelo desde un archivo .pkl"""

    
    model = mlflow.sklearn.load_model(
    model_uri=f"models:/{model_name}/Production"
    )
    """
    model_uri=f"models:/{model_name}/latest"
    model = mlflow.pyfunc.load_model(model_uri)
    """
    return model


@app.get("/models")
def list_models():
    """Lista los modelos disponibles en la carpeta /models"""

    # Fetch all registered models
    models = client.search_registered_models()
    versions = []
    
    if len(models)>0:
        # Get the latest model version
        for model in models:
            latest_model_versions = client.search_model_versions(f"name='{model.name}'")
            latest_version = max(int(m.version) for m in latest_model_versions)  # Get the highest version
            versions.append(latest_version)
            print(f'{model.name}:{latest_version}')
        
        out = [f'{model.name}:{vs}' for model, vs in zip(models,versions)]
    else:
        out = [] 

    # Print model names
    return out
  

import time

# Métricas Prometheus
REQUEST_COUNT = Counter('predict_requests_total', 'Total de peticiones de predicción')
REQUEST_LATENCY = Histogram('predict_latency_seconds', 'Tiempo de latencia de predicción')

@app.post("/predict/{model_name}")
def predict(model_name: str,input_data: PredictionInput):

    REQUEST_COUNT.inc()

    with REQUEST_LATENCY.time():

        """Realiza una predicción con el modelo especificado"""
        try:
            model = load_model(model_name)
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al cargar el modelo: {str(e)}")

        # Convertir la entrada a DataFrame si el modelo requiere ese formato
        try:
            numerical = [
                input_data.bed,
                input_data.bath,
                input_data.acre_lot,
                input_data.zip_code,
                input_data.house_size

            ]

            categorical = [
                input_data.city,
                input_data.state,
                input_data.street,
                input_data.brokered_by,
                input_data.prev_sold_date
            ]

            data_dict = {
                'bed': [input_data.bed],
                'bath': [input_data.bath],
                'acre_lot': [input_data.acre_lot],
                'street': [input_data.street],  # cuidado si esto es una string compleja
                'zip_code': [input_data.zip_code],
                'house_size': [input_data.house_size],
                'city': [input_data.city],
                'state': [input_data.state],
                'brokered_by': [input_data.brokered_by],
                'prev_sold_date': [input_data.prev_sold_date]  # asegúrate que sea el tipo correcto
            }

            # Crear un DataFrame
            input_df = pd.DataFrame(data_dict)

            numerical = np.array(numerical).reshape(1, -1)
            predictions = model.predict(input_df)

            # Guardar en la base de datos
            session = SessionLocal()
            ins = predictions_table.insert().values(
                model_name=model_name,
                city=input_data.city,
                state=input_data.state,
                brokered_by=input_data.brokered_by,
                price=float(predictions),
                bed=input_data.bed,
                bath=input_data.bath,
                acre_lot=input_data.acre_lot,
                street=input_data.street,
                zip_code=input_data.zip_code,
                house_size=input_data.house_size,
                prev_sold_date=input_data.prev_sold_date
            )
            session.execute(ins)
            session.commit()
            session.close()

            return {"predictions": predictions.tolist()}
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error en la predicción: {str(e)}")

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/annotations")
def annotations():

    # Get experiment by name
    experiment = client.get_experiment_by_name('argocd_experiment')
    if experiment is None:
        raise ValueError(f"Experiment argocd_experiment not found")
        
    # Search runs with the name filter
    runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=["attributes.start_time DESC"],
            max_results=10
        )
    
    all_annotations = ""
    #filter_string=f"tags.`mlflow.runName` = 'svm_validation'",
        
    if not runs:
        print(f"No runs found with name containing '{run_name_pattern}'")

    if len(runs)>0:     
        for run in runs:
            run_id = run.info.run_id
        
        # Get annotation if exists (adjust path as needed)
            try:
                annotation_content = mlflow.artifacts.load_text(
                        f"runs:/{run_id}/annotations/log.txt"
                    )
                print(annotation_content)
                all_annotations = all_annotations + "\n " + annotation_content
            except Exception as e:
                print(f"Annotation not found: {str(e)}")
                all_annotations = all_annotations + "\n " + f"no hay anotaciones para {run_id}"
    
        return all_annotations
    