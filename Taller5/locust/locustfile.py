from locust import HttpUser, task, between

class UsuarioDeCarga(HttpUser):
    wait_time = between(1, 2.5)

    @task
    def hacer_inferencia(self):
        model_name = "svm-model"
        payload = {
        "Soil_Type": 0,
        "Cover_Type": 0,
        "Elevation": 0.0,
        "Aspect": 0.0,
        "Slope": 0.0,
        "Horizontal_Distance_To_Hydrology": 0.0,
        "Vertical_Distance_To_Hydrology": 0.0,
        "Horizontal_Distance_To_Roadways": 0.0,
        "Hillshade_9am": 0.0,
        "Hillshade_Noon": 0.0,
        "Hillshade_3pm": 0.0,
        "Horizontal_Distance_To_Fire_Points": 0.0,
        "Wilderness_Area": 0
        }
        # Enviar una petición POST al endpoint /predict
        with self.client.post(f"/predict/{model_name}", json=payload, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"❌ Error: {response.status_code} - {response.text}")