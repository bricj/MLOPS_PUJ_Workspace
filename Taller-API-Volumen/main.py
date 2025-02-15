import os
import pickle
import pandas as pd
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import logging
import os

# Ruta donde están los modelos dentro del contenedor Docker
MODEL_DIR = "./models"

# Configurar el logger
log_file_path = './logs/mi_app.log'
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

app = FastAPI()

class PredictionInput(BaseModel):
    data: List[List[float]]  # Lista de listas con los datos de entrada

# Configuracion del logger
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

def load_model(model_name: str):
    """Carga un modelo desde un archivo .pkl"""
    model_path = os.path.join(MODEL_DIR, model_name)
    if not os.path.exists(model_path):
        raise HTTPException(status_code=404, detail="Modelo no encontrado")
    
    with open(model_path, "rb") as f:
        return pickle.load(f)


@app.get("/models")
def list_models():
    """Lista los modelos disponibles en la carpeta /models"""
    models = [f for f in os.listdir(MODEL_DIR) if f.endswith(".pkl")]
    return {"available_models": models}

@app.get("/model-schema/{model_name}")
def get_model_schema(model_name: str) -> Dict[str, Any]:
    """Obtiene la estructura esperada de los datos de entrada para hacer una predicción"""
    try:
        model = load_model(model_name)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cargar el modelo: {str(e)}")

    schema = {"model_name": model_name}

    # Intentar obtener nombres de columnas si existen
    if hasattr(model, "feature_names_in_"):
        input_features = list(model.feature_names_in_)
    else:
        input_features = ["feature_" + str(i) for i in range(model.n_features_in_)]

    schema["input_features"] = input_features

    # Generar un ejemplo de entrada
    schema["example_input"] = {
        "data": [[0.0 for _ in range(len(input_features))]]
    }

    return schema


@app.post("/predict/{model_name}")
def predict(model_name: str, input_data: PredictionInput):
    """Realiza una predicción con el modelo especificado"""
    try:
        model = load_model(model_name)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cargar el modelo: {str(e)}")

    # Convertir la entrada a DataFrame si el modelo requiere ese formato
    try:
        input_df = pd.DataFrame(input_data.data)
        predictions = model.predict(input_df)
        return {"predictions": predictions.tolist()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la predicción: {str(e)}")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f'petición recibida: {request.method}{request.url}')
    response = await call_next(request)
    logger.info(f'Respuesta enviada: {response.status_code}')
    return response
