from fastapi.testclient import TestClient

from app.main import app


def test_health_is_available() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_reports_test_mode_configuration() -> None:
    response = TestClient(app).get("/health")

    assert response.json()["razorpay_test_client_configured"] is True
