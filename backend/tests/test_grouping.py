from datetime import date

from app.services.grouping import bucket_posted_date


def test_bucket_today():
    assert bucket_posted_date(date.today(), date.today()) == "today"
