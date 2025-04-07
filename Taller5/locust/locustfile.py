from locust import HttpUser, task, between
from numpy import random as r

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
        # Enviar una petición POST al endpoint /predict
        
        response = self.client.post(f"/predict/{model_name}", json=payload)
        # Opcional: validación de respuesta
        if response.status_code != 200:
            print("❌ Error en la inferencia:", response.text)