from dataclasses import asdict, dataclass


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


def serialize_day_payloads(day_payloads: list[DayBucketSnapshot]) -> list[dict]:
    return [asdict(day_payload) for day_payload in day_payloads]
