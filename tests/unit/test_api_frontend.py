from fastapi.testclient import TestClient

from app.interfaces.api import app


client = TestClient(app)


def test_dashboard_root_serves_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Flood Watch HK" in response.text


def test_recent_runs_endpoint_returns_list():
    response = client.get("/api/runs/recent")
    assert response.status_code == 200
    payload = response.json()
    assert "runs" in payload
    assert isinstance(payload["runs"], list)
