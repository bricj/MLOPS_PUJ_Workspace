from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import uvicorn
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
import logging

# Instancia de la aplicación FastAPI
app = FastAPI()

import logging

# Configure logging
logging.basicConfig(
    filename='app.log',          # Name of the log file
    level=logging.INFO,          # Logging level (INFO, DEBUG, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s',  # Log format
    datefmt='%Y-%m-%d %H:%M:%S'  # Date/Time format
)

# Intentar cargar los modelos
try:
    model = joblib.load("model_logreg.pkl")
except Exception as e:
    print(f"Error cargando model_logreg.pkl: {e}")
    model = None

try:
    model_data = joblib.load('best_model_config.joblib')
    best_model = model_data['model']
    best_params = model_data['params']
    scaler = model_data['scaler']
    le_sex = model_data['label_encoder_sex']
    le_species = model_data['label_encoder_species']
    numerical_cols = model_data['numerical_cols']
    best_model.set_params(**best_params)
except Exception as e:
    print(f"Error cargando best_model_config.joblib: {e}")
    best_model = None

# Definiendo el modelo de datos para predicción
class InputData(BaseModel):
    Island_Indicar_0_1_2: int
    Culmen_Length_Entre0y1: float
    Culmen_Depth_Entre0y1: float
    Flipper_Length_Entre0y1: float
    Body_Mass_Entre0y1: float
    Sex_0_1: int
    Delta_15_Entre0y1: float
    Delta_13_Entre0y1: float

@app.post("/logistic_regression")
async def predict(data: InputData):
    if model is None:
        return {"error": "El modelo no se cargó correctamente"}
    
    input_data = np.array([
        data.Island_Indicar_0_1_2, data.Culmen_Length_Entre0y1, data.Culmen_Depth_Entre0y1, data.Flipper_Length_Entre0y1, 
        data.Body_Mass_Entre0y1, data.Sex_0_1, data.Delta_15_Entre0y1, data.Delta_13_Entre0y1
    ]).reshape(1, -1)
    
    prediction = model.predict(input_data)[0].item()
    #logs
    logging.info(f'predicción realizada con regresión logística \n\n \
                 entradas: \n \
                 {input_data} \n\n \
                 salida: \n \
                 {prediction}')
    
    return {"prediction": prediction}

# Definiendo el modelo de datos para los pingüinos
class Penguin(BaseModel):
    Culmen_Length_mm: float
    Culmen_Depth_mm: float
    Flipper_Length_mm: float
    Body_Mass_mm: float
    Sex_MALE_FEMALE: str

@app.post("/random_forest")
async def infer_specie(feature: Penguin):
    if best_model is None:
        return {"error": "El modelo no se cargó correctamente"}

    numerical = np.array([
        feature.Culmen_Length_mm, 
        feature.Culmen_Depth_mm, 
        feature.Flipper_Length_mm, 
        feature.Body_Mass_mm
    ]).reshape(1, -1)
    
    numerical = scaler.transform(numerical)
    features = np.append(numerical, le_sex.transform(np.array([feature.Sex_MALE_FEMALE])))
    entrada = features.reshape(1, -1)

    resultado = best_model.predict(entrada)
    specie = le_species.inverse_transform(resultado.tolist())[0]
    #logs
    logging.info(f'predicción realizada con bosque aleatorio \n\n \
                 entradas: \n \
                 {numerical} \n\n \
                 salida: \n \
                 {specie}')

    return {"Especie": specie}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8989)
