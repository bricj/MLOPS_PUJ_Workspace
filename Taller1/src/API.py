from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
import joblib
from fastapi import FastAPI
from pydantic import BaseModel
import numpy as np

# Carga de la configuracion del modelo
model_data = joblib.load('best_model_config.joblib')
best_model = model_data['model']
best_params = model_data['params']
scaler = model_data['scaler']
le_sex = model_data['label_encoder_sex']
le_species = model_data['label_encoder_species']
numerical_cols = model_data['numerical_cols']

# Seteo del modelo
best_model.set_params(**best_params)

# Instancia de la aplicación FastAPI
app = FastAPI()

# Definiendo un modelo de datos
class Penguin(BaseModel):
    Culmen_Length: float
    Culmen_Depth: float
    Flipper_Length: float
    Body_Mass: float
    Sex: str


@app.post("/Penguin/")
def infer_specie(feature: Penguin):

    numerical = [
        feature.Culmen_Length, 
        feature.Culmen_Depth, 
        feature.Flipper_Length, 
        feature.Body_Mass
        ]
    numerical = np.array(numerical).reshape(1, -1)
    numerical = scaler.transform(numerical)
    features = np.append(numerical,le_sex.transform(np.array([feature.Sex])))

    # Convertir los datos en formato adecuado para el modelo
    entrada = features.reshape(1, -1)

    # Hacer la predicción
    resultado = best_model.predict(entrada)
    specie = le_species.inverse_transform(resultado.tolist())[0]

    return {"Especie": specie}