from datetime import date, timedelta


def bucket_posted_date(posted_date: date, today: date) -> str:
    days_ago = (today - posted_date).days
    if 0 <= days_ago < 3:
        return "within_3_days"
    if 3 <= days_ago < 7:
        return "within_7_days"
    return "earlier"
