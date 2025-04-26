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

# Ruta donde están los modelos dentro del contenedor Docker
MODEL_DIR = "http://mlflow:5000"
mlflow.set_tracking_uri(MODEL_DIR)
client = mlflow.tracking.MlflowClient(tracking_uri=MODEL_DIR) 

# import os
os.environ['MLFLOW_S3_ENDPOINT_URL'] = "http://minio:9000"
os.environ['AWS_ACCESS_KEY_ID'] = 'admin'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'supersecret'

app = FastAPI()

class PredictionInput(BaseModel):
    Soil_Type: int
    Cover_Type: int
    Elevation: float
    Aspect: float
    Slope: float
    Horizontal_Distance_To_Hydrology: float
    Vertical_Distance_To_Hydrology: float
    Horizontal_Distance_To_Roadways: float
    Hillshade_9am: float
    Hillshade_Noon: float
    Hillshade_3pm: float
    Horizontal_Distance_To_Fire_Points: float
    Wilderness_Area: int


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

    # Print model names
    return [f'{model.name}:{vs}' for model, vs in zip(models,versions)]
  

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
                input_data.Soil_Type
                ,input_data.Cover_Type
                ,input_data.Elevation
                ,input_data.Aspect
                ,input_data.Slope
                ,input_data.Horizontal_Distance_To_Hydrology
                ,input_data.Vertical_Distance_To_Hydrology
                ,input_data.Horizontal_Distance_To_Roadways
                ,input_data.Hillshade_9am
                ,input_data.Hillshade_Noon
                ,input_data.Hillshade_3pm
                ,input_data.Horizontal_Distance_To_Fire_Points
                ,input_data.Wilderness_Area
            ]

            numerical = np.array(numerical).reshape(1, -1)
            predictions = model.predict(numerical)

            logging.info(f'predicción realizada con {model_name} \n \
                        entradas: {input_data} \n \
                        salida: {predictions}')

            return {"predictions": predictions.tolist()}
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error en la predicción: {str(e)}")

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)