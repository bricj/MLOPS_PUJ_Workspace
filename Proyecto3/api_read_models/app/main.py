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
MODEL_DIR = "http://10.43.101.168:31485" #Mlflow
mlflow.set_tracking_uri(MODEL_DIR)
client = mlflow.tracking.MlflowClient(tracking_uri=MODEL_DIR) 

# import os
os.environ['MLFLOW_S3_ENDPOINT_URL'] = "http://10.43.101.168:30921" #minio
os.environ['AWS_ACCESS_KEY_ID'] = 'minioadmin'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'minioadmin123'

app = FastAPI()

class PredictionInput(BaseModel):
    race: int
    gender: int
    age: int
    admission_type_id: int
    discharge_disposition_id: int
    admission_source_id: int
    diabetesMed: int
    max_glu_serum: int
    A1Cresult: int
    time_in_hospital: int
    num_lab_procedures: int
    num_procedures: int
    num_medications: int
    number_outpatient: int
    number_emergency: int
    number_inpatient: int
    number_diagnoses: int


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
                input_data.race,
                input_data.gender,
                input_data.age,
                input_data.admission_type_id,
                input_data.discharge_disposition_id,
                input_data.admission_source_id,
                input_data.diabetesMed,
                input_data.max_glu_serum,
                input_data.A1Cresult,
                input_data.time_in_hospital,
                input_data.num_lab_procedures,
                input_data.num_procedures,
                input_data.num_medications,
                input_data.number_outpatient,
                input_data.number_emergency,
                input_data.number_inpatient,
                input_data.number_diagnoses

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