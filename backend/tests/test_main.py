import logging

from app.main import run_startup_audits


class DummySessionContext:
    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, tb):
        return False


def test_run_startup_audits_skips_when_flag_disabled(monkeypatch):
    monkeypatch.setattr("app.main.settings.bounty_pool_estimated_bounty_startup_audit_enabled", False)
    called: list[bool] = []
    monkeypatch.setattr(
        "app.main.audit_estimated_bounties",
        lambda db, *, today, window_days: called.append(True),
    )

    run_startup_audits()

    assert called == []


def test_run_startup_audits_logs_warning_without_raising(monkeypatch, caplog):
    monkeypatch.setattr("app.main.settings.bounty_pool_estimated_bounty_startup_audit_enabled", True)
    monkeypatch.setattr("app.main.SessionLocal", lambda: DummySessionContext())
    monkeypatch.setattr(
        "app.main.audit_estimated_bounties",
        lambda db, *, today, window_days: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with caplog.at_level(logging.WARNING):
        run_startup_audits()

    assert "Estimated bounty startup audit failed" in caplog.text


def test_run_startup_audits_logs_summary_when_enabled(monkeypatch, caplog):
    monkeypatch.setattr("app.main.settings.bounty_pool_estimated_bounty_startup_audit_enabled", True)
    monkeypatch.setattr("app.main.settings.bounty_pool_estimated_bounty_audit_window_days", 21)
    monkeypatch.setattr("app.main.SessionLocal", lambda: DummySessionContext())
    monkeypatch.setattr(
        "app.main.audit_estimated_bounties",
        lambda db, *, today, window_days: {
            "strict_readiness": True,
            "window_days": window_days,
        },
    )

    with caplog.at_level(logging.INFO):
        run_startup_audits()

    assert '"strict_readiness": true' in caplog.text
    assert '"window_days": 21' in caplog.text
