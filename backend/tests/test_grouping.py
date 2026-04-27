from datetime import date, timedelta

from app.services.grouping import bucket_posted_date


def test_bucket_recent_3_days():
    today = date.today()

    assert bucket_posted_date(today, today) == "within_3_days"
    assert bucket_posted_date(today - timedelta(days=1), today) == "within_3_days"
    assert bucket_posted_date(today - timedelta(days=2), today) == "within_3_days"


def test_bucket_7_days_excludes_recent_3_days():
    today = date.today()

    assert bucket_posted_date(today - timedelta(days=3), today) == "within_7_days"
    assert bucket_posted_date(today - timedelta(days=6), today) == "within_7_days"


def test_bucket_earlier_starts_after_7_days():
    today = date.today()

    assert bucket_posted_date(today - timedelta(days=7), today) == "earlier"
