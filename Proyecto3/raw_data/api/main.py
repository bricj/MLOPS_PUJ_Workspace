from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import os
import requests

app = FastAPI()

# Configuración global
DATA_ROOT = './data/Diabetes'
DATA_FILEPATH = os.path.join(DATA_ROOT, 'Diabetes.csv')
BATCH_SIZE = 15000

def load_and_split_data():
    # Descargar si no existe
    os.makedirs(DATA_ROOT, exist_ok=True)
    if not os.path.isfile(DATA_FILEPATH):
        url = 'https://docs.google.com/uc?export=download&confirm={{VALUE}}&id=1k5-1caezQ3zWJbKaiMULTGq-3sz6uThC'
        r = requests.get(url, allow_redirects=True, stream=True)
        open(DATA_FILEPATH, 'wb').write(r.content)

    # Cargar datos
    df = pd.read_csv(DATA_FILEPATH)

    # Partición fija: 60% train, 20% val, 20% test
    train_val, test = train_test_split(
        df, test_size=0.15, random_state=42, stratify=df["readmitted"]
    )
    train, val = train_test_split(
        train_val, test_size=0.2143, random_state=42, stratify=train_val["readmitted"]
    )

    return train, val, test

def convert_numpy(obj):
    if isinstance(obj, np.generic):
        return obj.item()  # convierte por ejemplo np.int64 → int
    elif isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
        return None  # valores no válidos en JSON se convierten a None
    elif isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}  # recursivo
    elif isinstance(obj, list):
        return [convert_numpy(i) for i in obj]  # recursivo
    return obj  #

@app.post("/get-total-batches/")
def get_total_batches():
    train, val, test = load_and_split_data()
    
    # Calcular el total de batches para el conjunto de entrenamiento
    n_train_rows = len(train)
    total_train_batches = np.ceil(n_train_rows / BATCH_SIZE).astype(int)

    # Para el último batch (que incluye val + test)
    total_batches = total_train_batches + 1  # +1 para el batch final (val + test)

    return {"total_batches": int(total_batches)}

@app.get("/get-batch/")
def get_batch(batch_number: int):
    train, val, test = load_and_split_data()
    
    # Seleccionar el conjunto de datos train
    data = train
    n_rows = len(data)
    
    # Para el último batch (batch final), devolver tanto val como test
    if batch_number == -1:
        data = pd.concat([val, test], axis=0)
        n_rows = len(data)

    start_idx = batch_number * BATCH_SIZE
    end_idx = min(start_idx + BATCH_SIZE, n_rows)

    if start_idx >= n_rows:
        raise HTTPException(status_code=404, detail="Batch number out of range.")

    batch = data.iloc[start_idx:end_idx]
    #batch = batch.head(10)

    cleaned_batch = convert_numpy(batch.to_dict(orient="records"))

    return JSONResponse(content={
        "batch_number": batch_number,
        "start_row": start_idx,
        "end_row": end_idx,
        "batch_size": len(batch),
        "data": cleaned_batch
    })
