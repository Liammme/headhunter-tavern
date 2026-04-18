from app.services.feed_snapshot import DayBucketSnapshot, FeedMetadata, serialize_day_payloads, serialize_feed_metadata


def assemble_home_payload(*, intelligence: dict, day_payloads: list[DayBucketSnapshot], meta: FeedMetadata) -> dict:
    return {
        "intelligence": intelligence,
        "meta": serialize_feed_metadata(meta),
        "days": serialize_day_payloads(day_payloads),
    }
