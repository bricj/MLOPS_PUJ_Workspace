from fastapi.testclient import TestClient
from app.main import app  # Ajusta este import si tu archivo principal tiene otro nombre

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"
    assert "model_loaded" in data
    assert isinstance(data["model_loaded"], bool)

def test_prediction_success():
    sample_input = {
        "Elevation": 2800,
        "Aspect": 90,
        "Slope": 15,
        "Horizontal_Distance_To_Hydrology": 120,
        "Vertical_Distance_To_Hydrology": 30,
        "Horizontal_Distance_To_Roadways": 200,
        "Hillshade_9am": 220,
        "Hillshade_Noon": 240,
        "Hillshade_3pm": 180,
        "Horizontal_Distance_To_Fire_Points": 150,
        "Wilderness_Area": 1,
        "Soil_Type": 3
    }

    response = client.post("/predict", json=sample_input)
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert isinstance(data["prediction"], int)
    assert data["success"] is True

def test_prediction_missing_field():
    invalid_input = {
        # Elevation is missing
        "Aspect": 90,
        "Slope": 15,
        "Horizontal_Distance_To_Hydrology": 120,
        "Vertical_Distance_To_Hydrology": 30,
        "Horizontal_Distance_To_Roadways": 200,
        "Hillshade_9am": 220,
        "Hillshade_Noon": 240,
        "Hillshade_3pm": 180,
        "Horizontal_Distance_To_Fire_Points": 150,
        "Wilderness_Area": 1,
        "Soil_Type": 3
    }

    response = client.post("/predict", json=invalid_input)
    assert response.status_code == 422  # Unprocessable Entity por validación de Pydantic
