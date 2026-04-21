from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta

from app.services.scoring import DEFAULT_BOUNTY_RULE_VERSION

ANALYSIS_VERSION = "feed-v1"
WINDOW_DAYS = 14


@dataclass(frozen=True)
class FeedMetadata:
    analysis_version: str
    rule_version: str
    window_start: str
    window_end: str
    generated_at: str


@dataclass(frozen=True)
class JobFeedSnapshot:
    id: int
    title: str
    canonical_url: str
    bounty_grade: str
    tags: list[str]
    claimed_names: list[str]


@dataclass(frozen=True)
class CompanyFeedSnapshot:
    company: str
    company_grade: str
    total_jobs: int
    claimed_names: list[str]
    jobs: list[JobFeedSnapshot]


@dataclass(frozen=True)
class DayBucketSnapshot:
    bucket: str
    companies: list[CompanyFeedSnapshot]


def build_feed_metadata(now: datetime) -> FeedMetadata:
    window_end = now.date()
    window_start = window_end - timedelta(days=WINDOW_DAYS - 1)
    return FeedMetadata(
        analysis_version=ANALYSIS_VERSION,
        rule_version=DEFAULT_BOUNTY_RULE_VERSION,
        window_start=window_start.isoformat(),
        window_end=window_end.isoformat(),
        generated_at=now.replace(microsecond=0).isoformat(),
    )


def serialize_day_payloads(day_payloads: list[DayBucketSnapshot]) -> list[dict]:
    return [asdict(day_payload) for day_payload in day_payloads]


def serialize_feed_metadata(meta: FeedMetadata) -> dict:
    return asdict(meta)
