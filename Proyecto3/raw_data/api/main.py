from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import os
import requests
import logging
from typing import Dict, List, Any, Optional
from functools import lru_cache

# Configuraci�n de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("data_service")

app = FastAPI(
    title="Diabetes Dataset API",
    description="API para disponibilizar datos de diabetes en batches",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producci�n, especificar dominios exactos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuraci�n global
DATA_ROOT = './data/Diabetes'
DATA_FILEPATH = os.path.join(DATA_ROOT, 'Diabetes.csv')
BATCH_SIZE = 15000

# Modelos para respuestas
class BatchInfo(BaseModel):
    total_batches: int = Field(..., description="N�mero total de batches disponibles")
    
class DatasetInfo(BaseModel):
    train_size: int = Field(..., description="N�mero total de registros en el conjunto de entrenamiento")
    validation_size: int = Field(..., description="N�mero total de registros en el conjunto de validaci�n")
    test_size: int = Field(..., description="N�mero total de registros en el conjunto de prueba")
    batch_size: int = Field(..., description="Tama�o de los batches configurado")

class BatchData(BaseModel):
    batch_number: int = Field(..., description="N�mero del batch actual")
    start_row: int = Field(..., description="�ndice inicial del batch")
    end_row: int = Field(..., description="�ndice final del batch")
    batch_size: int = Field(..., description="Tama�o del batch actual")
    data: List[Dict[str, Any]] = Field(..., description="Datos del batch")

# Singleton para cargar los datos solo una vez
@lru_cache(maxsize=1)
def get_data_cache():
    """Carga los datos una sola vez y los mantiene en memoria"""
    logger.info("Cargando datos en cach�...")
    train, val, test = load_and_split_data()
    return {"train": train, "val": val, "test": test}

def load_and_split_data():
    """Carga y divide los datos en conjuntos de entrenamiento, validaci�n y prueba"""
    # Descargar si no existe
    os.makedirs(DATA_ROOT, exist_ok=True)
    if not os.path.isfile(DATA_FILEPATH):
        try:
            logger.info("Descargando dataset de diabetes...")
            # URL correcto de Google Drive (requiere implementaci�n espec�fica para Drive)
            url = 'https://drive.google.com/uc?export=download&id=1k5-1caezQ3zWJbKaiMULTGq-3sz6uThC'
            r = requests.get(url, allow_redirects=True, stream=True)
            if r.status_code != 200:
                logger.error(f"Error descargando datos: {r.status_code}")
                raise Exception(f"Error al descargar datos: {r.status_code}")
                
            with open(DATA_FILEPATH, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info("Dataset descargado correctamente")
        except Exception as e:
            logger.error(f"Error al descargar el dataset: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al descargar el dataset: {str(e)}"
            )
    
    try:
        # Cargar datos
        logger.info("Cargando dataset desde archivo local...")
        df = pd.read_csv(DATA_FILEPATH)
        
        # Verificar que los datos tengan la columna esperada
        if "readmitted" not in df.columns:
            raise ValueError("El dataset no contiene la columna 'readmitted'")
            
        # Partici�n fija: 60% train, 20% val, 20% test
        train_val, test = train_test_split(
            df, test_size=0.2, random_state=42, stratify=df["readmitted"]
        )
        train, val = train_test_split(
            train_val, test_size=0.25, random_state=42, stratify=train_val["readmitted"]
        )
        
        logger.info(f"Dataset dividido: train={len(train)}, val={len(val)}, test={len(test)} registros")
        return train, val, test
        
    except Exception as e:
        logger.error(f"Error al procesar el dataset: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar el dataset: {str(e)}"
        )

def convert_numpy(obj):
    """Convierte tipos de NumPy a tipos nativos de Python para serializaci�n JSON"""
    if isinstance(obj, np.generic):
        return obj.item()  # convierte por ejemplo np.int64 � int
    elif isinstance(obj, (float, np.float64, np.float32)) and (np.isnan(obj) or np.isinf(obj)):
        return None  # valores no v�lidos en JSON se convierten a None
    elif isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}  # recursivo
    elif isinstance(obj, list):
        return [convert_numpy(i) for i in obj]  # recursivo
    return obj

@app.on_event("startup")
async def startup_event():
    """Inicializa la cach� de datos al arrancar la aplicaci�n"""
    try:
        # Precarga los datos en la cach�
        get_data_cache()
        logger.info("Datos precargados correctamente")
    except Exception as e:
        logger.error(f"Error al precargar los datos: {str(e)}")

@app.post("/get-total-batches/", response_model=BatchInfo, status_code=status.HTTP_200_OK)
def get_total_batches():
    """
    Obtiene el n�mero total de batches disponibles para el conjunto de entrenamiento
    
    Returns:
        BatchInfo: Objeto con el n�mero total de batches
    """
    try:
        data_cache = get_data_cache()
        train = data_cache["train"]
        
        # Calcular el total de batches para el conjunto de entrenamiento
        n_train_rows = len(train)
        total_train_batches = np.ceil(n_train_rows / BATCH_SIZE).astype(int)
        
        logger.info(f"Total de batches de entrenamiento calculado: {total_train_batches}")
        return {"total_batches": int(total_train_batches)}
    except Exception as e:
        logger.error(f"Error al calcular el total de batches: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al calcular el total de batches: {str(e)}"
        )

@app.get("/get-batch/", response_model=BatchData, status_code=status.HTTP_200_OK)
def get_batch(
    batch_number: int = Query(..., description="N�mero de batch a obtener"),
    limit: Optional[int] = Query(None, description="L�mite opcional de registros a devolver")
):
    """
    Obtiene un batch espec�fico de datos del conjunto de entrenamiento
    
    Args:
        batch_number: N�mero del batch a obtener
        limit: L�mite opcional de registros a devolver
        
    Returns:
        BatchData: Objeto con los datos del batch solicitado
    """
    try:
        if batch_number < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El n�mero de batch debe ser mayor o igual a 0"
            )
        
        data_cache = get_data_cache()
        train = data_cache["train"]
        
        # Seleccionar el conjunto de datos train
        data = train
        n_rows = len(data)
        start_idx = batch_number * BATCH_SIZE
            
        if start_idx >= n_rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Batch {batch_number} fuera de rango. M�ximo: {int(np.ceil(n_rows / BATCH_SIZE) - 1)}"
            )
            
        end_idx = min(start_idx + BATCH_SIZE, n_rows)
        batch = data.iloc[start_idx:end_idx]
        
        # Aplicar l�mite si se especifica
        if limit and limit > 0 and limit < len(batch):
            batch = batch.head(limit)
            
        cleaned_batch = convert_numpy(batch.to_dict(orient="records"))
        
        logger.info(f"Batch de entrenamiento {batch_number} enviado: {len(batch)} registros")
        return {
            "batch_number": batch_number,
            "start_row": int(start_idx),
            "end_row": int(end_idx),
            "batch_size": len(batch),
            "data": cleaned_batch
        }
    except HTTPException:
        # Re-lanzar excepciones HTTP ya formateadas
        raise
    except Exception as e:
        logger.error(f"Error al obtener batch {batch_number}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener batch {batch_number}: {str(e)}"
        )

@app.get("/get-validation-batch/", response_model=BatchData, status_code=status.HTTP_200_OK)
def get_validation_batch(
    batch_number: int = Query(0, description="N�mero de batch a obtener"),
    limit: Optional[int] = Query(None, description="L�mite opcional de registros a devolver")
):
    """
    Obtiene un batch espec�fico de datos del conjunto de validaci�n
    
    Args:
        batch_number: N�mero del batch a obtener
        limit: L�mite opcional de registros a devolver
        
    Returns:
        BatchData: Objeto con los datos del batch solicitado
    """
    try:
        if batch_number < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El n�mero de batch debe ser mayor o igual a 0"
            )
        
        data_cache = get_data_cache()
        val = data_cache["val"]
        
        # Seleccionar el conjunto de datos de validaci�n
        data = val
        n_rows = len(data)
        start_idx = batch_number * BATCH_SIZE
            
        if start_idx >= n_rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Batch {batch_number} fuera de rango. M�ximo: {int(np.ceil(n_rows / BATCH_SIZE) - 1)}"
            )
            
        end_idx = min(start_idx + BATCH_SIZE, n_rows)
        batch = data.iloc[start_idx:end_idx]
        
        # Aplicar l�mite si se especifica
        if limit and limit > 0 and limit < len(batch):
            batch = batch.head(limit)
            
        cleaned_batch = convert_numpy(batch.to_dict(orient="records"))
        
        logger.info(f"Batch de validaci�n {batch_number} enviado: {len(batch)} registros")
        return {
            "batch_number": batch_number,
            "start_row": int(start_idx),
            "end_row": int(end_idx),
            "batch_size": len(batch),
            "data": cleaned_batch
        }
    except HTTPException:
        # Re-lanzar excepciones HTTP ya formateadas
        raise
    except Exception as e:
        logger.error(f"Error al obtener batch de validaci�n {batch_number}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener batch de validaci�n {batch_number}: {str(e)}"
        )

@app.get("/get-test-batch/", response_model=BatchData, status_code=status.HTTP_200_OK)
def get_test_batch(
    batch_number: int = Query(0, description="N�mero de batch a obtener"),
    limit: Optional[int] = Query(None, description="L�mite opcional de registros a devolver")
):
    """
    Obtiene un batch espec�fico de datos del conjunto de prueba
    
    Args:
        batch_number: N�mero del batch a obtener
        limit: L�mite opcional de registros a devolver
        
    Returns:
        BatchData: Objeto con los datos del batch solicitado
    """
    try:
        if batch_number < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El n�mero de batch debe ser mayor o igual a 0"
            )
        
        data_cache = get_data_cache()
        test = data_cache["test"]
        
        # Seleccionar el conjunto de datos de prueba
        data = test
        n_rows = len(data)
        start_idx = batch_number * BATCH_SIZE
            
        if start_idx >= n_rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Batch {batch_number} fuera de rango. M�ximo: {int(np.ceil(n_rows / BATCH_SIZE) - 1)}"
            )
            
        end_idx = min(start_idx + BATCH_SIZE, n_rows)
        batch = data.iloc[start_idx:end_idx]
        
        # Aplicar l�mite si se especifica
        if limit and limit > 0 and limit < len(batch):
            batch = batch.head(limit)
            
        cleaned_batch = convert_numpy(batch.to_dict(orient="records"))
        
        logger.info(f"Batch de prueba {batch_number} enviado: {len(batch)} registros")
        return {
            "batch_number": batch_number,
            "start_row": int(start_idx),
            "end_row": int(end_idx),
            "batch_size": len(batch),
            "data": cleaned_batch
        }
    except HTTPException:
        # Re-lanzar excepciones HTTP ya formateadas
        raise
    except Exception as e:
        logger.error(f"Error al obtener batch de prueba {batch_number}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener batch de prueba {batch_number}: {str(e)}"
        )

@app.post("/get-total-validation-batches/", response_model=BatchInfo, status_code=status.HTTP_200_OK)
def get_total_validation_batches():
    """
    Obtiene el n�mero total de batches disponibles para el conjunto de validaci�n
    
    Returns:
        BatchInfo: Objeto con el n�mero total de batches
    """
    try:
        data_cache = get_data_cache()
        val = data_cache["val"]
        
        # Calcular el total de batches para el conjunto de validaci�n
        n_val_rows = len(val)
        total_val_batches = np.ceil(n_val_rows / BATCH_SIZE).astype(int)
        
        logger.info(f"Total de batches de validaci�n calculado: {total_val_batches}")
        return {"total_batches": int(total_val_batches)}
    except Exception as e:
        logger.error(f"Error al calcular el total de batches de validaci�n: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al calcular el total de batches de validaci�n: {str(e)}"
        )

@app.post("/get-total-test-batches/", response_model=BatchInfo, status_code=status.HTTP_200_OK)
def get_total_test_batches():
    """
    Obtiene el n�mero total de batches disponibles para el conjunto de prueba
    
    Returns:
        BatchInfo: Objeto con el n�mero total de batches
    """
    try:
        data_cache = get_data_cache()
        test = data_cache["test"]
        
        # Calcular el total de batches para el conjunto de prueba
        n_test_rows = len(test)
        total_test_batches = np.ceil(n_test_rows / BATCH_SIZE).astype(int)
        
        logger.info(f"Total de batches de prueba calculado: {total_test_batches}")
        return {"total_batches": int(total_test_batches)}
    except Exception as e:
        logger.error(f"Error al calcular el total de batches de prueba: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al calcular el total de batches de prueba: {str(e)}"
        )

@app.get("/dataset-info", response_model=DatasetInfo, status_code=status.HTTP_200_OK)
def get_dataset_info():
    """
    Obtiene informaci�n sobre los conjuntos de datos cargados
    
    Returns:
        DatasetInfo: Objeto con informaci�n sobre los conjuntos de datos
    """
    try:
        data_cache = get_data_cache()
        train, val, test = data_cache["train"], data_cache["val"], data_cache["test"]
        
        info = {
            "train_size": len(train),
            "validation_size": len(val),
            "test_size": len(test),
            "batch_size": BATCH_SIZE
        }
        
        logger.info(f"Informaci�n del dataset solicitada: {info}")
        return info
    except Exception as e:
        logger.error(f"Error al obtener informaci�n del dataset: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener informaci�n del dataset: {str(e)}"
        )

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Endpoint para verificar la salud del servicio"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)