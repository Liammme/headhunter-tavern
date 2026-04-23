from collections.abc import Sequence

from app.core.config import settings
from app.models import Job
from app.services.bounty_estimation import BountyEstimate, RULE_VERSION

PENDING_ESTIMATED_BOUNTY_LABEL = "待估算"
ALLOWED_CONFIDENCE_VALUES = {"low", "medium", "high"}


def should_expose_estimated_bounty() -> bool:
    return settings.bounty_pool_estimated_bounty_read_enabled


def select_readable_estimated_bounty(jobs: Sequence[Job]) -> BountyEstimate | None:
    for job in jobs:
        estimate = read_estimated_bounty(job)
        if estimate is not None:
            return estimate
    return None


def read_estimated_bounty(job: Job) -> BountyEstimate | None:
    signal_tags = job.signal_tags if isinstance(job.signal_tags, dict) else None
    estimate = BountyEstimate.from_signal_tags(signal_tags)
    if estimate is None:
        return None
    if estimate.rule_version != RULE_VERSION:
        return None
    if estimate.min_amount > estimate.amount or estimate.amount > estimate.max_amount:
        return None
    if estimate.rate_pct < 10 or estimate.rate_pct > 20:
        return None
    if estimate.confidence not in ALLOWED_CONFIDENCE_VALUES:
        return None
    return estimate
