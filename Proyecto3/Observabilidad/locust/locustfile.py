from locust import HttpUser, task, between
from numpy import random as r
import logging
import time
import os

# Configurar logging
logging.basicConfig(
    filename="/app/locust_logs.log",
    filemode="a",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

replicas = os.getenv("REPLICA_COUNT", "No especificado")
cpu_limit = os.getenv("CPU_LIMIT", "No especificado")
mem_limit = os.getenv("MEM_LIMIT", "No especificado")

logging.info(f"Iniciando prueba - replicas: {replicas}")
logging.info(f"Iniciando prueba - cpu: {cpu_limit}")
logging.info(f"Iniciando prueba - memoria: {mem_limit}")


class UsuarioDeCarga(HttpUser):
    wait_time = between(1, 2.5)

    @task
    def hacer_inferencia(self):
        model_name = "svm-model"
        payload = {
        "Soil_Type": r.randint(1,high=3),
        "Cover_Type": r.randint(1,high=3),
        "Elevation": r.rand(),
        "Aspect": r.rand(),
        "Slope": r.rand(),
        "Horizontal_Distance_To_Hydrology": r.rand(),
        "Vertical_Distance_To_Hydrology": r.rand(),
        "Horizontal_Distance_To_Roadways": r.rand(),
        "Hillshade_9am": r.rand(),
        "Hillshade_Noon": r.rand(),
        "Hillshade_3pm": r.rand(),
        "Horizontal_Distance_To_Fire_Points": r.rand(),
        "Wilderness_Area": r.randint(1,high=3)
        }
        
        # Medir tiempo de respuesta
        inicio = time.time()
        response = self.client.post(f"/predict/{model_name}", json=payload)
        fin = time.time()
        duracion = round(fin - inicio, 4)  # en segundos

        # Enviar una petición POST al endpoint /predict
        response = self.client.post(f"/predict/{model_name}", json=payload)
        # Opcional: validación de respuesta
        if response.status_code == 200:
            logging.info(f"✅ Éxito - Tiempo: {duracion}s - Status: {response.status_code}")
        else:
            logging.error(f"❌ Error - Tiempo: {duracion}s - Status: {response.status_code} - Respuesta: {response.text} - Payload: {payload}")