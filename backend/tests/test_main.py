from app.main import app


def test_app_title_is_configured():
    assert app.title == "Bounty Pool API"
