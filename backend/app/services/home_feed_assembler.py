from app.services.feed_snapshot import DayBucketSnapshot, serialize_day_payloads


def assemble_home_payload(*, intelligence: dict, day_payloads: list[DayBucketSnapshot]) -> dict:
    return {
        "intelligence": intelligence,
        "days": serialize_day_payloads(day_payloads),
    }
