from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_detailed_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert "timestamp" in response.json()
    assert response.json()["status"] == "healthy"
