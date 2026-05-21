import pytest
import json

from app.cli import generate_japan_market_report as cli


def test_generate_japan_market_report_help_uses_executable_init_db_command(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--help"])

    output = capsys.readouterr().out
    normalized_output = " ".join(output.split())
    assert exc_info.value.code == 0
    assert 'python -c "from app.db.init_db import init_db; init_db()"' in normalized_output
    assert "python -m app.db.init_db" not in normalized_output
    assert "python -m app.cli.crawl_japan_jobs" in normalized_output
    assert "python -m app.cli.generate_japan_market_report --days 180 --min-age-days 3" in normalized_output
    assert "sudo systemctl status bounty-pool --no-pager" in normalized_output


class _Session:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_generate_japan_market_report_cli_defaults_to_three_day_gate(monkeypatch, capsys):
    monkeypatch.setattr(cli, "init_db", lambda: None)
    monkeypatch.setattr(cli, "SessionLocal", lambda: _Session())
    monkeypatch.setattr(cli, "JAPAN_ADAPTERS", {})
    monkeypatch.setattr(
        cli,
        "refresh_living_market_report_if_due",
        lambda db, days, min_age_days, region, adapters: {
            "status": "skipped",
            "days": days,
            "min_age_days": min_age_days,
            "region": region,
            "adapter_count": len(adapters),
        },
    )

    cli.main(["--days", "180"])

    assert json.loads(capsys.readouterr().out) == {
        "status": "skipped",
        "days": 180,
        "min_age_days": 3,
        "region": "japan",
        "adapter_count": 0,
    }
