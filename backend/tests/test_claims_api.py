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


def test_claims_preflight_allows_127_localhost_frontend(client):
    response = client.options(
        "/api/v1/claims",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"


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


def test_create_claim_returns_409_when_company_already_claimed(client, db_session):
    first_job = build_job()
    second_job = build_job()
    second_job.canonical_url = "https://jobs.example.com/acme/staff-engineer"
    second_job.title = "Staff Engineer"
    db_session.add_all([first_job, second_job])
    db_session.commit()
    db_session.refresh(first_job)
    db_session.refresh(second_job)

    first_response = client.post(
        "/api/v1/claims",
        json={"job_id": first_job.id, "claimer_name": "Liam"},
    )
    second_response = client.post(
        "/api/v1/claims",
        json={"job_id": second_job.id, "claimer_name": "Mina"},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert second_response.json() == {"detail": "Company already claimed"}
