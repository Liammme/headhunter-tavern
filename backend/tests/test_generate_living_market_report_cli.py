import json

from app.cli import generate_living_market_report as cli


class _Session:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_generate_living_market_report_cli_baseline_smoke(monkeypatch, capsys):
    monkeypatch.setattr(cli, "init_db", lambda: None)
    monkeypatch.setattr(cli, "SessionLocal", lambda: _Session())
    monkeypatch.setattr(
        cli,
        "generate_living_market_report",
        lambda db, mode, days: {"status": "success", "mode": mode, "days": days},
    )

    cli.main(["--mode", "baseline", "--days", "180"])

    assert json.loads(capsys.readouterr().out) == {
        "status": "success",
        "mode": "baseline",
        "days": 180,
    }


def test_generate_living_market_report_cli_update_smoke(monkeypatch, capsys):
    monkeypatch.setattr(cli, "init_db", lambda: None)
    monkeypatch.setattr(cli, "SessionLocal", lambda: _Session())
    monkeypatch.setattr(
        cli,
        "generate_living_market_report",
        lambda db, mode, days: {"status": "success", "mode": mode, "days": days},
    )

    cli.main(["--mode", "update", "--days", "180"])

    assert json.loads(capsys.readouterr().out)["mode"] == "update"
