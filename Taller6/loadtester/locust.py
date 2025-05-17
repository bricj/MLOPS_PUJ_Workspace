from locust import HttpUser, task, between
import json
import random
import numpy as np

class MLModelUser(HttpUser):
    wait_time = between(1, 3)  # Tiempo de espera entre solicitudes (1-3 segundos)
    
    @task
    def predict(self):
        # Opción 1: Modelo con claves específicas para cada característica
        # Simula las características reales que espera tu modelo
        payload = {
            "Elevation": random.uniform(1800, 3800),  # Elevación en metros
            "Aspect": random.uniform(0, 360),  # Orientación en grados
            "Slope": random.uniform(0, 60),  # Pendiente en grados
            "Horizontal_Distance_To_Hydrology": random.uniform(0, 1400),  # Distancia en metros
            "Vertical_Distance_To_Hydrology": random.uniform(-500, 700),  # Distancia vertical (puede ser negativa)
            "Horizontal_Distance_To_Roadways": random.uniform(0, 7000),  # Distancia en metros
            "Hillshade_9am": random.randint(0, 255),  # Índice de sombra (0-255)
            "Hillshade_Noon": random.randint(0, 255),  # Índice de sombra (0-255)
            "Hillshade_3pm": random.randint(0, 255),  # Índice de sombra (0-255)
            "Horizontal_Distance_To_Fire_Points": random.uniform(0, 7000),  # Distancia en metros
            "Wilderness_Area": random.randint(0, 3),  # 4 áreas posibles (0-3)
            "Soil_Type": random.randint(0, 39)  # 40 tipos de suelo posibles (0-39)
        }
        
        try:
            # Realizar la solicitud POST al endpoint de predicción
            response = self.client.post(
                "/predict",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            # Registrar información adicional sobre la respuesta
            if response.status_code == 200:
                # Registrar detalles de la respuesta exitosa
                prediction = response.json()
                print(f"Predicción recibida: {prediction}")
            else:
                # Registrar detalles del error
                print(f"Error en la solicitud: {response.status_code}, {response.text}")
                
        except Exception as e:
            print(f"Excepción durante la solicitud: {str(e)}")
    
    @task(3)  # Esta tarea se ejecutará 3 veces menos frecuentemente que la tarea predict
    def health_check(self):
        # Verificar el estado de salud de la API
        try:
            response = self.client.get("/health")
            
            if response.status_code == 200:
                print("Servicio saludable ✅")
            else:
                print(f"Servicio no saludable ❌ - {response.status_code}")
        except Exception as e:
            print(f"Excepción durante health check: {str(e)}")