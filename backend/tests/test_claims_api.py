from app.models import Job


def build_job() -> Job:
    return Job(
        canonical_url="https://jobs.example.com/acme/founding-engineer",
        source_name="test",
        title="Founding Engineer",
        company="Acme",
        company_normalized="acme",
        description="Build the core platform.",
    )


def test_create_claim_requires_name(client):
    response = client.post("/api/v1/claims", json={"job_id": 1, "claimer_name": ""})

    assert response.status_code == 422


def test_create_claim_returns_created_claim(client, db_session):
    job = build_job()
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    response = client.post(
        "/api/v1/claims",
        json={"job_id": job.id, "claimer_name": "  Liam  "},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "job_id": job.id,
        "claimer_name": "Liam",
    }


def test_create_claim_returns_404_when_job_missing(client):
    response = client.post("/api/v1/claims", json={"job_id": 999, "claimer_name": "Liam"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
