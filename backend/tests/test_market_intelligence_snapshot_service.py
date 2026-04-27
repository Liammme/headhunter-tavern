import json
from datetime import date, datetime

from sqlalchemy import select

from app.models import Job, MarketIntelligenceSnapshot
from app.services.market_intelligence_report import MarketIntelligenceReportError


FULL_DESCRIPTION = (
    "Build LLM serving, RAG systems, Kubernetes model deployment, "
    "and enterprise AI platform."
)


def _load_snapshot_service():
    from app.services import market_intelligence_snapshot_service

    return market_intelligence_snapshot_service


def _add_job(db_session, *, job_id: int = 1, posted_at: datetime | None = None) -> Job:
    job = Job(
        id=job_id,
        canonical_url=f"https://jobs.example.com/{job_id}",
        source_name="demo-board",
        title="AI Infrastructure Engineer",
        company="OpenGradient",
        company_normalized="opengradient",
        description=FULL_DESCRIPTION,
        posted_at=posted_at or datetime(2026, 4, 25, 9, 0, 0),
        collected_at=datetime(2026, 4, 25, 10, 0, 0),
        job_category="技术",
        domain_tag="AI",
        bounty_grade="high",
        signal_tags={
            "claimed_names": ["Alice"],
            "bd_entry": "email",
            "salary": "100K-200K",
        },
    )
    db_session.add(job)
    db_session.commit()
    return job


def _fixed_clock() -> datetime:
    return datetime(2026, 4, 26, 14, 30, 15, 123456)


def test_generate_daily_market_intelligence_snapshot_persists_success_snapshot(
    db_session,
    monkeypatch,
):
    service = _load_snapshot_service()
    _add_job(db_session)
    report_payload = {
        "headline": "AI infra demand is broadening",
        "narrative": "30d demand remains visible in the 90d window.",
    }

    def fake_generate_market_report(signal_payload):
        assert db_session.in_transaction() is False
        return report_payload

    monkeypatch.setattr(service, "generate_market_report", fake_generate_market_report)

    result = service.generate_daily_market_intelligence_snapshot(
        db_session,
        clock=_fixed_clock,
    )

    snapshot = db_session.execute(select(MarketIntelligenceSnapshot)).scalar_one()
    assert result == {"status": "success", "snapshot_id": snapshot.id}
    assert snapshot.snapshot_date == date(2026, 4, 26)
    assert snapshot.generated_at == datetime(2026, 4, 26, 14, 30, 15)
    assert snapshot.window_days == 90
    assert snapshot.status == "success"
    assert snapshot.error_message is None
    assert snapshot.model_name is None
    assert snapshot.report_payload["headline"] == "AI infra demand is broadening"

    serialized_signal = json.dumps(snapshot.market_signal_payload, ensure_ascii=False)
    assert "canonical_url" not in serialized_signal
    assert "source_name" not in serialized_signal
    assert "https://jobs.example.com" not in serialized_signal
    assert "demo-board" not in serialized_signal
    assert "bounty" not in serialized_signal
    assert "claimed" not in serialized_signal
    assert "bd_entry" not in serialized_signal
    assert FULL_DESCRIPTION not in serialized_signal


def test_generate_daily_market_intelligence_snapshot_persists_failed_snapshot(
    db_session,
    monkeypatch,
):
    service = _load_snapshot_service()
    _add_job(db_session)

    def raise_report_error(signal_payload):
        raise RuntimeError("model timed out after 30 seconds")

    monkeypatch.setattr(service, "generate_market_report", raise_report_error)

    result = service.generate_daily_market_intelligence_snapshot(
        db_session,
        snapshot_date=date(2026, 4, 26),
        clock=_fixed_clock,
    )

    snapshot = db_session.execute(select(MarketIntelligenceSnapshot)).scalar_one()
    assert result["status"] == "failed"
    assert "model timed out" in result["error"]
    assert snapshot.status == "failed"
    assert snapshot.snapshot_date == date(2026, 4, 26)
    assert snapshot.generated_at == datetime(2026, 4, 26, 14, 30, 15)
    assert snapshot.report_payload == {}
    assert snapshot.error_message == result["error"]
    assert "model timed out" in snapshot.error_message


def test_generate_daily_market_intelligence_snapshot_persists_fallback_snapshot_on_quality_gate_failure(
    db_session,
    monkeypatch,
):
    service = _load_snapshot_service()
    _add_job(db_session)

    def raise_quality_gate_error(signal_payload):
        raise MarketIntelligenceReportError("report contains banned phrase: bd")

    monkeypatch.setattr(service, "generate_market_report", raise_quality_gate_error)

    result = service.generate_daily_market_intelligence_snapshot(
        db_session,
        snapshot_date=date(2026, 4, 26),
        clock=_fixed_clock,
    )

    snapshot = db_session.execute(select(MarketIntelligenceSnapshot)).scalar_one()
    assert result == {"status": "fallback", "snapshot_id": snapshot.id}
    assert snapshot.status == "fallback"
    assert snapshot.snapshot_date == date(2026, 4, 26)
    assert snapshot.report_payload["headline"] == "Market demand remains selective"
    assert snapshot.error_message == "report contains banned phrase: bd"


def test_generate_daily_market_intelligence_snapshot_redacts_secrets_from_errors(
    db_session,
    monkeypatch,
):
    service = _load_snapshot_service()
    _add_job(db_session)

    def raise_secret_error(signal_payload):
        raise RuntimeError(
            "provider failed: sk-test-redact-me "
            "api_key=plain-api-secret token=plain-token-secret "
            "password=plain-password-secret "
            "api_key: colon-api-secret token: colon-token-secret "
            "password: colon-password-secret "
            "OPENAI_API_KEY=env-openai-secret "
            "BOUNTY_POOL_ZHIPU_API_KEY=env-zhipu-secret "
            "access_token=env-access-token-secret "
            "Authorization: Bearer bearer-token-secret "
            "postgresql://user:db-password-secret@example.com:5432/app "
            "postgres://user:postgres-password-secret@example.com:5432/app "
            "mysql://user:mysql-password-secret@example.com:3306/app"
        )

    monkeypatch.setattr(service, "generate_market_report", raise_secret_error)

    result = service.generate_daily_market_intelligence_snapshot(
        db_session,
        snapshot_date=date(2026, 4, 26),
        clock=_fixed_clock,
    )

    snapshot = db_session.execute(select(MarketIntelligenceSnapshot)).scalar_one()
    combined = f"{result['error']} {snapshot.error_message}"
    assert result["status"] == "failed"
    assert "[redacted]" in combined
    assert "sk-test-redact-me" not in combined
    assert "plain-api-secret" not in combined
    assert "plain-token-secret" not in combined
    assert "plain-password-secret" not in combined
    assert "colon-api-secret" not in combined
    assert "colon-token-secret" not in combined
    assert "colon-password-secret" not in combined
    assert "env-openai-secret" not in combined
    assert "env-zhipu-secret" not in combined
    assert "env-access-token-secret" not in combined
    assert "bearer-token-secret" not in combined
    assert "db-password-secret" not in combined
    assert "postgres-password-secret" not in combined
    assert "mysql-password-secret" not in combined
    assert "postgresql://user:db-password-secret" not in combined
    assert "postgres://user:postgres-password-secret" not in combined
    assert "mysql://user:mysql-password-secret" not in combined
