from fastapi import FastAPI, HTTPException, Request, Response
import joblib
import logging
import numpy as np
from pydantic import BaseModel
import os
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

DATA_PATH = "/api/data/covertype.csv" 
DATA_OUTPUT = "/api/model/"

app = FastAPI()

class PredictionInput(BaseModel):
    """Modelo de datos para la entrada de predicción"""
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
    Soil_Type: int

# Cargar modelo una sola vez al iniciar
try:
    model = joblib.load(DATA_OUTPUT + "model_svm.pkl")
    logging.info("Modelo cargado correctamente")
except Exception as e:
    logging.error(f"Error al cargar el modelo: {str(e)}")
    model = None

# Métricas Prometheus
REQUEST_COUNT = Counter('predict_requests_total', 'Total de peticiones de predicción')
REQUEST_LATENCY = Histogram('predict_latency_seconds', 'Tiempo de latencia de predicción')

@app.post("/predict")
def predict(input_data: PredictionInput):
    """Realiza una predicción directamente sin transformaciones adicionales"""
    REQUEST_COUNT.inc()

    with REQUEST_LATENCY.time():
        if model is None:
            raise HTTPException(status_code=500, detail="El modelo no se cargó correctamente")
        
        try:
            # Convertir input_data a lista de valores
            features = [
                input_data.Elevation,
                input_data.Aspect,
                input_data.Slope,
                input_data.Horizontal_Distance_To_Hydrology,
                input_data.Vertical_Distance_To_Hydrology,
                input_data.Horizontal_Distance_To_Roadways,
                input_data.Hillshade_9am,
                input_data.Hillshade_Noon,
                input_data.Hillshade_3pm,
                input_data.Horizontal_Distance_To_Fire_Points,
                input_data.Wilderness_Area,
                input_data.Soil_Type
            ]
            
            # Crear el array numpy directamente
            features_array = np.array(features).reshape(1, -1)
            
            # Realizar predicción
            predictions = model.predict(features_array)
            
            logging.info(f'Predicción realizada: {predictions[0]}')
            
            return {
                "prediction": int(predictions[0]),
                "success": True
            }
        except Exception as e:
            logging.error(f"Error en predicción: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error en la predicción: {str(e)}")

@app.get("/health")
def health_check():
    """Endpoint para verificar el estado de la API"""
    return {"status": "healthy", "model_loaded": model is not None}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)



# from fastapi import FastAPI, HTTPException
# import joblib
# import csv
# import logging
# import numpy as np
# from pydantic import BaseModel


# DATA_PATH = "./api/data/covertype.csv" 
# DATA_OUTPUT = "./api/app/"

# app = FastAPI()

# class PredictionInput(BaseModel):
#     Soil_Type: int
#     Cover_Type: int
#     Elevation: float
#     Aspect: float
#     Slope: float
#     Horizontal_Distance_To_Hydrology: float
#     Vertical_Distance_To_Hydrology: float
#     Horizontal_Distance_To_Roadways: float
#     Hillshade_9am: float
#     Hillshade_Noon: float
#     Hillshade_3pm: float
#     Horizontal_Distance_To_Fire_Points: float
#     Wilderness_Area: int

# # Configuracion del logger
# logging.basicConfig(
#     filename='./mi_app.log',
#     level=logging.INFO,
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# )

# @app.post("/predict/{model_name}")
# def predict(input_data: PredictionInput):
#     """Realiza una predicción con el modelo especificado"""

#     # Cargar los datos del archivo CSV
#     data = []
#     with open(DATA_PATH, newline='') as csvfile:
#         reader = csv.reader(csvfile)
#         next(reader, None)
#         for row in reader:
#             data.append(row)
#     model = joblib.load(DATA_OUTPUT + "model_svm.pkl")

#     # Convertir la entrada a DataFrame si el modelo requiere ese formato
#     try:
#         numerical = [
#             input_data.Soil_Type
#             ,input_data.Cover_Type
#             ,input_data.Elevation
#             ,input_data.Aspect
#             ,input_data.Slope
#             ,input_data.Horizontal_Distance_To_Hydrology
#             ,input_data.Vertical_Distance_To_Hydrology
#             ,input_data.Horizontal_Distance_To_Roadways
#             ,input_data.Hillshade_9am
#             ,input_data.Hillshade_Noon
#             ,input_data.Hillshade_3pm
#             ,input_data.Horizontal_Distance_To_Fire_Points
#             ,input_data.Wilderness_Area
#         ]

#         numerical = np.array(numerical).reshape(1, -1)
#         predictions = model.predict(numerical)

#         logging.info(f'predicción realizada con model_svm.pkl \n \
#                     entradas: {input_data} \n \
#                     salida: {predictions}')

#         return {"predictions": predictions.tolist()}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error en la predicción: {str(e)}")
