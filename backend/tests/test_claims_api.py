from fastapi.testclient import TestClient

from app.main import app


def test_create_claim_requires_name():
    client = TestClient(app)

    response = client.post("/api/v1/claims", json={"job_id": 1, "claimer_name": ""})

    assert response.status_code == 422
