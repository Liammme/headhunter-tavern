from collections.abc import Sequence

from app.core.config import settings
from app.models import Job
from app.services.bounty_estimation import BountyEstimate, read_bounty_estimate_from_signal_tags

PENDING_ESTIMATED_BOUNTY_LABEL = "待估算"


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
    return read_bounty_estimate_from_signal_tags(signal_tags)
