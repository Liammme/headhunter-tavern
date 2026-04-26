from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping, Protocol


RULE_VERSION = "bounty-rule-v2"
BD_FEE_SHARE_PCT = 10
HEADHUNTER_FEE_RATE_RANGE = (20, 30)
ESTIMATED_BOUNTY_SIGNAL_TAG_KEYS = (
    "estimated_bounty_amount",
    "estimated_bounty_label",
    "estimated_bounty_min",
    "estimated_bounty_max",
    "estimated_bounty_rate_pct",
    "estimated_bounty_rule_version",
    "estimated_bounty_confidence",
)
ALLOWED_BOUNTY_CONFIDENCE_VALUES = {"low", "medium", "high"}


@dataclass(frozen=True)
class BountyEstimateInput:
    category: str
    seniority: str
    domain_tag: str
    urgent: bool
    critical: bool
    hard_to_fill: bool
    role_complexity: str
    business_criticality: str
    compensation_signal: str
    company_signal: str
    time_pressure_signals: tuple[str, ...]
    annual_salary_range: tuple[int, int] | None = None


class SupportsBountyEstimateFacts(Protocol):
    category: str
    seniority: str
    domain_tag: str
    urgent: bool
    critical: bool
    hard_to_fill: bool
    role_complexity: str
    business_criticality: str
    compensation_signal: str
    company_signal: str
    time_pressure_signals: tuple[str, ...]
    annual_salary_range: tuple[int, int] | None


@dataclass(frozen=True)
class BountyEstimate:
    amount: int
    min_amount: int
    max_amount: int
    rate_pct: int
    label: str
    confidence: str
    rule_version: str

    def to_signal_tags(self) -> dict[str, int | str]:
        return {
            "estimated_bounty_amount": self.amount,
            "estimated_bounty_label": self.label,
            "estimated_bounty_min": self.min_amount,
            "estimated_bounty_max": self.max_amount,
            "estimated_bounty_rate_pct": self.rate_pct,
            "estimated_bounty_rule_version": self.rule_version,
            "estimated_bounty_confidence": self.confidence,
        }

    @classmethod
    def from_signal_tags(cls, signal_tags: Mapping[str, object] | None) -> "BountyEstimate" | None:
        if signal_tags is None:
            return None

        amount = signal_tags.get("estimated_bounty_amount")
        label = signal_tags.get("estimated_bounty_label")
        min_amount = signal_tags.get("estimated_bounty_min")
        max_amount = signal_tags.get("estimated_bounty_max")
        rate_pct = signal_tags.get("estimated_bounty_rate_pct")
        rule_version = signal_tags.get("estimated_bounty_rule_version")
        confidence = signal_tags.get("estimated_bounty_confidence")

        if not all(isinstance(value, int) for value in (amount, min_amount, max_amount, rate_pct)):
            return None
        if not all(isinstance(value, str) and value.strip() for value in (label, rule_version, confidence)):
            return None

        return cls(
            amount=amount,
            min_amount=min_amount,
            max_amount=max_amount,
            rate_pct=rate_pct,
            label=label.strip(),
            confidence=confidence.strip(),
            rule_version=rule_version.strip(),
        )


def estimate_bounty(input: BountyEstimateInput) -> BountyEstimate | None:
    if input.annual_salary_range is None:
        return None

    annual_min, annual_max = _normalize_salary_range_for_estimation(input.annual_salary_range)
    headhunter_min_pct, headhunter_max_pct = HEADHUNTER_FEE_RATE_RANGE
    min_amount = int(annual_min * headhunter_min_pct / 100 * BD_FEE_SHARE_PCT / 100)
    max_amount = int(annual_max * headhunter_max_pct / 100 * BD_FEE_SHARE_PCT / 100)
    amount = int((min_amount + max_amount) / 2)
    return BountyEstimate(
        amount=amount,
        min_amount=min_amount,
        max_amount=max_amount,
        rate_pct=BD_FEE_SHARE_PCT,
        label=f"¥{min_amount:,.0f}-¥{max_amount:,.0f}",
        confidence=_resolve_confidence(input.compensation_signal),
        rule_version=RULE_VERSION,
    )


def build_bounty_estimate_input_from_facts(facts: SupportsBountyEstimateFacts) -> BountyEstimateInput:
    return BountyEstimateInput(
        category=facts.category,
        seniority=facts.seniority,
        domain_tag=facts.domain_tag,
        urgent=facts.urgent,
        critical=facts.critical,
        hard_to_fill=facts.hard_to_fill,
        role_complexity=facts.role_complexity,
        business_criticality=facts.business_criticality,
        compensation_signal=facts.compensation_signal,
        company_signal=facts.company_signal,
        time_pressure_signals=facts.time_pressure_signals,
        annual_salary_range=facts.annual_salary_range,
    )


def classify_bounty_signal_tags(signal_tags: Mapping[str, object] | None) -> Literal["complete", "partial", "invalid", "missing"]:
    estimate = read_bounty_estimate_from_signal_tags(signal_tags)
    if estimate is not None:
        return "complete"

    normalized = signal_tags if signal_tags is not None else {}
    if any(key in normalized for key in ESTIMATED_BOUNTY_SIGNAL_TAG_KEYS):
        return "invalid" if BountyEstimate.from_signal_tags(normalized) is not None else "partial"
    return "missing"


def read_bounty_estimate_from_signal_tags(signal_tags: Mapping[str, object] | None) -> BountyEstimate | None:
    estimate = BountyEstimate.from_signal_tags(signal_tags)
    if estimate is None:
        return None
    if estimate.rule_version != RULE_VERSION:
        return None
    if estimate.min_amount > estimate.amount or estimate.amount > estimate.max_amount:
        return None
    if estimate.rate_pct != BD_FEE_SHARE_PCT:
        return None
    if estimate.confidence not in ALLOWED_BOUNTY_CONFIDENCE_VALUES:
        return None
    return estimate


def _resolve_confidence(compensation_signal: str) -> str:
    if compensation_signal == "strong":
        return "high"
    return "medium"


def _normalize_salary_range_for_estimation(annual_salary_range: tuple[int, int]) -> tuple[int, int]:
    annual_min, annual_max = annual_salary_range
    if annual_min <= 0 < annual_max:
        midpoint = int((annual_min + annual_max) / 2)
        return (midpoint, midpoint)
    return annual_min, annual_max
