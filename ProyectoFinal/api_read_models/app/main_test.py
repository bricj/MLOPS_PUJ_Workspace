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
import json

# Ruta donde están los modelos dentro del contenedor Docker
MODEL_DIR = "http://10.43.101.168:30500" #Mlflow
mlflow.set_tracking_uri(MODEL_DIR)
client = mlflow.tracking.MlflowClient(tracking_uri=MODEL_DIR) 

"""
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
    Column("price", Float),
    Column("acre_lot",Float),
    Column("house_size",Float),
    Column("rate_bath_bed",Float),
    Column("room_configuration_minimal_rooms",Float),
    Column("room_configuration_compact_rooms",Float),
    Column("room_configuration_standard_rooms",Float),
    Column("room_configuration_spacious_rooms",Float),
    Column("room_configuration_luxury_rooms",Float),
    Column("region_west",Float)
)

# Crear la tabla si no existe
metadata.create_all(bind=engine)
"""

app = FastAPI()

class PredictionInput(BaseModel):
    acre_lot: float
    house_size: float
    rate_bath_bed: float
    room_configuration_minimal_rooms: float
    room_configuration_compact_rooms: float
    room_configuration_standard_rooms: float
    room_configuration_spacious_rooms: float
    room_configuration_luxury_rooms: float
    region_west: float




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

def get_run_id_from_model(model_name:str, model_version:str):
    try:
        mv = client.get_model_version(name=model_name,version=model_version)
        return mv.run_id
    except Exception as e:
        raise ValueError(f"ID no encontrado para {model_name}:{model_version}")

def load_input_schema(run_id: str, artifact_path: str = "input_schema.json"):

    local_path = mlflow.artifacts.download_artifacts(
        run_id = run_id,
        artifact_path=artifact_path
    )

    with open(local_path, "r") as f:
        input_schema = json.load(f)
    return input_schema


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


@app.get("/model/get-schema")
def get_model_schema(model_name:str, model_version:str):
    run_id = get_run_id_from_model(model_name,model_version)
    schema = load_input_schema(run_id)
    return schema
    

import time

# Métricas Prometheus
REQUEST_COUNT = Counter('predict_requests_total', 'Total de peticiones de predicción')
REQUEST_LATENCY = Histogram('predict_latency_seconds', 'Tiempo de latencia de predicción')

@app.post("/predict/{model_name}")
def predict(model_name: str, input_data: PredictionInput):  # input_data: PredictionInput

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

            data_dict = {
                "acre_lot": [input_data.acre_lot],
                "house_size": [input_data.house_size],
                "rate_bath_bed": [input_data.rate_bath_bed],
                "room_configuration_minimal_rooms": [input_data.room_configuration_minimal_rooms],
                "room_configuration_compact_rooms": [input_data.room_configuration_compact_rooms],
                "room_configuration_standard_rooms": [input_data.room_configuration_standard_rooms],
                "room_configuration_spacious_rooms": [input_data.room_configuration_spacious_rooms],
                "room_configuration_luxury_rooms": [input_data.room_configuration_luxury_rooms],
                "region_west": [input_data.region_west]
            }

            # Crear un DataFrame
            input_df = pd.DataFrame(data_dict)
            """
            input_df = pd.DataFrame([body])
            """
            # numerical = np.array(numerical).reshape(1, -1)
            predictions = model.predict(input_df)

            """
            # Guardar en la base de datos
            
            session = SessionLocal()
            ins = predictions_table.insert().values(
                model_name=model_name,
                price=float(predictions),
                acre_lot=input_data.acre_lot,
                house_size=input_data.house_size,
                rate_bath_bed=input_data.rate_bath_bed,
                room_configuration_minimal_rooms=input_data.room_configuration_minimal_rooms,
                room_configuration_compact_rooms=input_data.room_configuration_compact_rooms,
                room_configuration_standard_rooms=input_data.room_configuration_standard_rooms,
                room_configuration_spacious_rooms=input_data.room_configuration_spacious_rooms,
                room_configuration_luxury_rooms=input_data.room_configuration_luxury_rooms,
                region_west=input_data.region_west
            )
            session.execute(ins)
            session.commit()
            session.close()
            
            """

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
            order_by=["attributes.start_time ASC"],
            max_results=100
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

@app.get("/health")
def health_check():
    """Endpoint para verificar el estado de la API"""
    return {"status": "healthy"}
    