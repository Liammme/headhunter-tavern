import json

from app.cli import refresh_living_market_report as cli


class _Session:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_refresh_living_market_report_cli_defaults_to_three_day_gate(monkeypatch, capsys):
    monkeypatch.setattr(cli, "init_db", lambda: None)
    monkeypatch.setattr(cli, "SessionLocal", lambda: _Session())
    monkeypatch.setattr(
        cli,
        "refresh_living_market_report_if_due",
        lambda db, days, min_age_days: {"status": "skipped", "days": days, "min_age_days": min_age_days},
    )

    cli.main(["--days", "180"])

    assert json.loads(capsys.readouterr().out) == {
        "status": "skipped",
        "days": 180,
        "min_age_days": 3,
    }
