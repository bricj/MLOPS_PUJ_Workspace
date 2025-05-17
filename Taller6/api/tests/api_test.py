from fastapi.testclient import TestClient
print(TestClient)
from app.main import app  # Ajusta este import si tu archivo principal tiene otro nombre.

client = TestClient(app)
a="a"

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

    response = client.post("/predict", json=sample_input)
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert isinstance(data["prediction"], int)
    assert data["success"] is True

def test_prediction_missing_field():
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

    response = client.post("/predict", json=invalid_input)
    assert response.status_code == 422  # Unprocessable Entity por validación de Pydantic
