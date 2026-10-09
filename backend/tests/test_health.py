from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify that root endpoint returns HTTP 200 and docs links."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "docs_url" in data
    assert data["docs_url"] == "/docs"
    assert "health_url" in data
    assert data["health_url"] == "/api/health"


def test_health_check_endpoint():
    """Verify that GET /api/health returns status ok with correct structure."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["message"] == "AI Chatbot backend is up and running!"
    assert data["version"] == "0.1.0"
    assert data["environment"] == "development"
