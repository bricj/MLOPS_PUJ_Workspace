# import pytest
# from fastapi.testclient import TestClient
# from app.main import app  # Ajusta este import si tu archivo principal tiene otro nombre.

# client = TestClient(app)

# def test_health_check():
#     """Verifica que el endpoint /health responda correctamente con estado 'healthy'."""
#     response = client.get("/health")
#     assert response.status_code == 200
#     data = response.json()
#     assert "status" in data
#     assert data["status"] == "healthy"
#     assert "model_loaded" in data
#     assert isinstance(data["model_loaded"], bool)

# def test_prediction_success():
#     """Verifica que el endpoint /predict procese correctamente una entrada válida."""
#     sample_input = {
#         "Elevation": 0,
#         "Aspect": 0,
#         "Slope": 0,
#         "Horizontal_Distance_To_Hydrology": 0,
#         "Vertical_Distance_To_Hydrology": 0,
#         "Horizontal_Distance_To_Roadways": 0,
#         "Hillshade_9am": 0,
#         "Hillshade_Noon": 0,
#         "Hillshade_3pm": 0,
#         "Horizontal_Distance_To_Fire_Points": 0,
#         "Wilderness_Area": 0,
#         "Soil_Type": 0
#     }
    
#     response = client.post(
#         "/predict", 
#         json=sample_input,
#         headers={"Content-Type": "application/json"}
#     )
    
#     assert response.status_code == 200
#     data = response.json()
#     assert "prediction" in data
#     assert isinstance(data["prediction"], int)
#     assert data["success"] is True
    
#     # Verificación opcional de tiempo de inferencia si tu API lo devuelve
#     # Si tu API no devuelve inference_time, puedes omitir estas líneas
#     if "inference_time" in data:
#         assert isinstance(data["inference_time"], float)

# def test_prediction_missing_field():
#     """Verifica que el endpoint /predict maneje correctamente entradas inválidas."""
#     invalid_input = {
#         # Elevation is missing for the experiment
#         "Aspect": 0,
#         "Slope": 0,
#         "Horizontal_Distance_To_Hydrology": 0,
#         "Vertical_Distance_To_Hydrology": 0,
#         "Horizontal_Distance_To_Roadways": 0,
#         "Hillshade_9am": 0,
#         "Hillshade_Noon": 0,
#         "Hillshade_3pm": 0,
#         "Horizontal_Distance_To_Fire_Points": 0,
#         "Wilderness_Area": 0,
#         "Soil_Type": 0
#     }
    
#     response = client.post(
#         "/predict", 
#         json=invalid_input,
#         headers={"Content-Type": "application/json"}
#     )
    
#     assert response.status_code == 422  # Unprocessable Entity por validación de Pydantic
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Mock global para la variable 'model'
@pytest.fixture(autouse=True)
def mock_model():
    """Simula que el modelo está cargado para todas las pruebas."""
    # Crear un mock para reemplazar la variable global 'model'
    mock_model = MagicMock()
    
    # Configurar el comportamiento del mock
    mock_model.predict.return_value = [1]  # Siempre devuelve clase 1
    
    # Parchear la variable global 'model' en el módulo app.main
    with patch('app.main.model', mock_model):
        yield mock_model

def test_health_check():
    """Verifica que el endpoint /health responda correctamente."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"
    assert "model_loaded" in data
    assert data["model_loaded"] is True  # Será True porque hemos hecho mock del modelo

def test_prediction_success():
    """Verifica que el endpoint /predict procese correctamente una entrada válida."""
    sample_input = {
        "Elevation": 0,
        "Aspect": 0,
        "Slope": 0,
        "Horizontal_Distance_To_Hydrology": 0,
        "Vertical_Distance_To_Hydrology": 0,
        "Horizontal_Distance_To_Roadways": 0,
        "Hillshade_9am": 0,
        "Hillshade_Noon": 0,
        "Hillshade_3pm": 0,
        "Horizontal_Distance_To_Fire_Points": 0,
        "Wilderness_Area": 0,
        "Soil_Type": 0
    }
    
    response = client.post(
        "/predict", 
        json=sample_input,
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert isinstance(data["prediction"], int)
    assert data["success"] is True

def test_prediction_missing_field():
    """Verifica que el endpoint /predict maneje correctamente entradas inválidas."""
    invalid_input = {
        # Elevation is missing for the experiment
        "Aspect": 0,
        "Slope": 0,
        "Horizontal_Distance_To_Hydrology": 0,
        "Vertical_Distance_To_Hydrology": 0,
        "Horizontal_Distance_To_Roadways": 0,
        "Hillshade_9am": 0,
        "Hillshade_Noon": 0,
        "Hillshade_3pm": 0,
        "Horizontal_Distance_To_Fire_Points": 0,
        "Wilderness_Area": 0,
        "Soil_Type": 0
    }
    
    response = client.post(
        "/predict", 
        json=invalid_input,
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 422  # Unprocessable Entity por validación de Pydantic
    