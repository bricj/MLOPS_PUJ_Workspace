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

def test_prediction_success():
    """Verifica que el endpoint /predict procese correctamente una entrada válida."""
    sample_input = {
        "acre_lot": 1,
        "house_size": 1,
        "rate_bath_bed": 1,
        "room_configuration_minimal_rooms": 0,
        "room_configuration_compact_rooms": 1,
        "room_configuration_standard_rooms": 0,
        "room_configuration_spacious_rooms": 0,
        "room_configuration_luxury_rooms": 0,
        "region_west": 1
    }
    
    response = client.post(
        "/predict/lasso-regressor", 
        json=sample_input,
        headers={"Content-Type": "application/json", "accept": "application/json"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert isinstance(data["prediction"], int)
    assert data["success"] is True

def test_prediction_missing_field():
    """Verifica que el endpoint /predict maneje correctamente entradas inválidas."""
    invalid_input = {
        # house_size is missing for the experiment
        "acre_lot": 1,
        "rate_bath_bed": 1,
        "room_configuration_minimal_rooms": 0,
        "room_configuration_compact_rooms": 1,
        "room_configuration_standard_rooms": 0,
        "room_configuration_spacious_rooms": 0,
        "room_configuration_luxury_rooms": 0,
        "region_west": 1
    }
    
    response = client.post(
        "/predict/lasso-regressor", 
        json=invalid_input,
        headers={"Content-Type": "application/json", "accept": "application/json"}
    )
    ########
    assert response.status_code == 422  # Hace falta campo y mlflow no permite hacer inferencia
