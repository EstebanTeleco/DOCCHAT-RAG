"""
test_api.py
Tests para los endpoints de api/main.py, usando TestClient de FastAPI
(no necesita levantar uvicorn de verdad, ni conexión a internet).
"""
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health_devuelve_200():
    """El endpoint /health debe responder con status code 200 (OK)."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_devuelve_status_ok():
    """El endpoint /health debe devolver exactamente {"status": "ok"}."""
    response = client.get("/health")
    assert response.json() == {"status": "ok"}