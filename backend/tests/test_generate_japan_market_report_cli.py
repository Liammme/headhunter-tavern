import pytest

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
    assert "python -m app.cli.generate_japan_market_report --days 180" in normalized_output
    assert "sudo systemctl status bounty-pool --no-pager" in normalized_output
