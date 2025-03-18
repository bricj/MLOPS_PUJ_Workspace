import os
import joblib
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import logging
import os
import mlflow

# Ruta donde están los modelos dentro del contenedor Docker
MODEL_DIR = "http://10.43.101.166:5000"
mlflow.set_tracking_uri(MODEL_DIR)

import os
os.environ['MLFLOW_S3_ENDPOINT_URL'] = "http://10.43.101.166:9000"
os.environ['AWS_ACCESS_KEY_ID'] = 'admin'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'supersecret'

app = FastAPI()

class PredictionInput(BaseModel):
    Island: int 
    Culmen_Length: float
    Culmen_Depth: float
    Flipper_Length: float
    Body_Mass: float
    Sex: int

# Configuracion del logger
logging.basicConfig(
    filename='./logs/mi_app.log',
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

def load_model(model_name: str, version: int):
    """Carga un modelo desde un archivo .pkl"""

    model = mlflow.pyfunc.load_model(
    model_uri=f"models:/{model_name}/{version}"
    )
    return model


@app.get("/models")
def list_models():
    """Lista los modelos disponibles en la carpeta /models"""
    client = mlflow.tracking.MlflowClient()
    # Listar modelos registrados en el Model Registry
    models = client.search_registered_models()
    model_info = [
        {
            "name": version.name,
            "current_stage": version.current_stage,
            "version": version.version
        }
        for model in models
        for version in model.latest_versions  # Aquí accedemos a latest_versions correctamente
    ]

    return {"available_models": model_info}

@app.post("/predict/{model_name}")
def predict(model_name: str, version: int ,input_data: PredictionInput):
    """Realiza una predicción con el modelo especificado"""
    try:
        model = load_model(f'{model_name}', f'{version}')
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cargar el modelo: {str(e)}")

    # Convertir la entrada a DataFrame si el modelo requiere ese formato
    try:
        numerical = [
            input_data.Island,
            input_data.Culmen_Length, 
            input_data.Culmen_Depth, 
            input_data.Flipper_Length, 
            input_data.Body_Mass,
            input_data.Sex,
        ]
        numerical = np.array(numerical).reshape(1, -1)
        predictions = model.predict(numerical)

        logging.info(f'predicción realizada con {model_name} \n \
                    entradas: {input_data} \n \
                    salida: {predictions}')

        return {"predictions": predictions.tolist()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la predicción: {str(e)}")
