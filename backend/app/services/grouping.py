from datetime import date, timedelta


def bucket_posted_date(posted_date: date, today: date) -> str:
    if posted_date == today:
        return "today"
    if posted_date == today - timedelta(days=1):
        return "yesterday"
    return "earlier"
