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
import os
import mlflow
import requests
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import create_engine, Table, Column, Integer, String, Float, MetaData
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

# Ruta donde están los modelos dentro del contenedor Docker
MODEL_DIR = "http://10.43.101.168:31485" #Mlflow
mlflow.set_tracking_uri(MODEL_DIR)
client = mlflow.tracking.MlflowClient(tracking_uri=MODEL_DIR) 

# import os
os.environ['MLFLOW_S3_ENDPOINT_URL'] = "http://10.43.101.168:30855" #minio
os.environ['AWS_ACCESS_KEY_ID'] = 'minioadmin'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'minioadmin123'

# URL de la base de datos de logs
DATABASE_URL = "postgresql://inference:inferencepass@10.43.101.166:5433/inference"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData()

# Definir la tabla (puedes ajustar tipos y nombres)
predictions_table = Table(
    "predictions", metadata,
    Column("id", Integer, primary_key=True, index=True, autoincrement=True),
    Column("model_name", String),
    Column("feature_1", Integer),
    Column("feature_2", Integer),
    Column("feature_3", Integer),
    Column("feature_4", Integer),
    Column("feature_5", Integer),
    Column("feature_6", Integer),
    Column("feature_7", Integer),
    Column("feature_8", Integer),
    Column("feature_9", Integer),
    Column("feature_10", Integer),
    Column("feature_11", Integer),
    Column("feature_12", Integer),
    Column("feature_13", Integer),
    Column("feature_14", Integer),
    Column("feature_15", Integer),
    Column("label", String)
)

# Crear la tabla si no existe
metadata.create_all(bind=engine)

app = FastAPI()

class PredictionInput(BaseModel):
    feature_1: int
    feature_2: int
    feature_3: int
    feature_4: int
    feature_5: int
    feature_6: int
    feature_7: int
    feature_8: int
    feature_9: int
    feature_10: int
    feature_11: int
    feature_12: int
    feature_13: int
    feature_14: int
    feature_15: int



# Configuracion del logger
logging.basicConfig(
    filename='./logs/mi_app.log',
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

def load_model(model_name: str):
    """Carga un modelo desde un archivo .pkl"""

    
    model = mlflow.pyfunc.load_model(
    model_uri=f"models:/{model_name}/latest"
    )
    """
    model_uri=f"models:/{model_name}/latest"
    model = mlflow.sklearn.load_model(model_uri)
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

        # Load the MLmodel metadata
        model_md = mlflow.models.Model.load(models[0].latest_versions[0].source)

        # Get the model signature (schema)
        signature = model_md.signature

        if signature:
            print("✅ Input Schema:", signature.inputs)
            print("✅ Output Schema:", signature.outputs)
        else:
            print("❌ No schema found for this model.")

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
                input_data.feature_1,
                input_data.feature_2,
                input_data.feature_3,
                input_data.feature_4,
                input_data.feature_5,
                input_data.feature_6,
                input_data.feature_7,
                input_data.feature_8,
                input_data.feature_9,
                input_data.feature_10,
                input_data.feature_11,
                input_data.feature_12,
                input_data.feature_13,
                input_data.feature_14,
                input_data.feature_15
            ]

            numerical = np.array(numerical).reshape(1, -1)
            predictions = model.predict(numerical)

            # Guardar en la base de datos
            session = SessionLocal()
            ins = predictions_table.insert().values(
                model_name=model_name,
                feature_1=input_data.feature_1,
                feature_2=input_data.feature_2,
                feature_3=input_data.feature_3,
                feature_4=input_data.feature_4,
                feature_5=input_data.feature_5,
                feature_6=input_data.feature_6,
                feature_7=input_data.feature_7,
                feature_8=input_data.feature_8,
                feature_9=input_data.feature_9,
                feature_10=input_data.feature_10,
                feature_11=input_data.feature_11,
                feature_12=input_data.feature_12,
                feature_13=input_data.feature_13,
                feature_14=input_data.feature_14,
                feature_15=input_data.feature_15,
                label=str(predictions)
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