from dataclasses import dataclass


RULE_VERSION = "bounty-rule-v1"


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


@dataclass(frozen=True)
class BountyEstimate:
    amount: int
    min_amount: int
    max_amount: int
    rate_pct: int
    label: str
    confidence: str
    rule_version: str


DEFAULT_ANNUAL_SALARY_BANDS = {
    "AI/算法": {
        "none": (240_000, 360_000),
        "senior": (360_000, 520_000),
        "staff": (500_000, 720_000),
        "principal": (600_000, 900_000),
        "lead": (480_000, 680_000),
        "architect": (550_000, 820_000),
        "director": (700_000, 1_100_000),
        "head": (780_000, 1_200_000),
        "vp": (900_000, 1_500_000),
        "founding": (650_000, 1_000_000),
    },
    "技术": {
        "none": (220_000, 320_000),
        "senior": (320_000, 460_000),
        "staff": (460_000, 680_000),
        "principal": (560_000, 820_000),
        "lead": (420_000, 620_000),
        "architect": (500_000, 760_000),
        "director": (650_000, 980_000),
        "head": (720_000, 1_080_000),
        "vp": (850_000, 1_350_000),
        "founding": (600_000, 900_000),
    },
    "数据": {
        "none": (200_000, 300_000),
        "senior": (300_000, 420_000),
        "staff": (420_000, 600_000),
        "principal": (520_000, 760_000),
        "lead": (400_000, 560_000),
        "architect": (460_000, 680_000),
        "director": (600_000, 900_000),
        "head": (680_000, 1_000_000),
        "vp": (780_000, 1_200_000),
        "founding": (560_000, 820_000),
    },
    "产品": {
        "none": (220_000, 320_000),
        "senior": (320_000, 460_000),
        "staff": (420_000, 620_000),
        "principal": (500_000, 760_000),
        "lead": (420_000, 620_000),
        "architect": (500_000, 760_000),
        "director": (620_000, 920_000),
        "head": (700_000, 1_000_000),
        "vp": (820_000, 1_260_000),
        "founding": (560_000, 820_000),
    },
    "增长": {
        "none": (180_000, 260_000),
        "senior": (260_000, 380_000),
        "staff": (320_000, 480_000),
        "principal": (380_000, 560_000),
        "lead": (340_000, 500_000),
        "architect": (380_000, 560_000),
        "director": (480_000, 720_000),
        "head": (560_000, 820_000),
        "vp": (680_000, 1_000_000),
        "founding": (420_000, 620_000),
    },
    "商务": {
        "none": (180_000, 260_000),
        "senior": (260_000, 380_000),
        "staff": (320_000, 480_000),
        "principal": (380_000, 560_000),
        "lead": (340_000, 500_000),
        "architect": (380_000, 560_000),
        "director": (480_000, 720_000),
        "head": (560_000, 820_000),
        "vp": (680_000, 1_000_000),
        "founding": (420_000, 620_000),
    },
    "运营": {
        "none": (160_000, 240_000),
        "senior": (220_000, 320_000),
        "staff": (280_000, 400_000),
        "principal": (320_000, 460_000),
        "lead": (300_000, 440_000),
        "architect": (320_000, 460_000),
        "director": (420_000, 620_000),
        "head": (500_000, 720_000),
        "vp": (620_000, 920_000),
        "founding": (360_000, 520_000),
    },
}


def estimate_bounty(input: BountyEstimateInput) -> BountyEstimate:
    annual_min, annual_max = _resolve_salary_band(input.category, input.seniority)
    rate_pct = _resolve_fee_rate_pct(input)
    min_amount = int(annual_min * rate_pct / 100)
    max_amount = int(annual_max * rate_pct / 100)
    amount = int((min_amount + max_amount) / 2)
    return BountyEstimate(
        amount=amount,
        min_amount=min_amount,
        max_amount=max_amount,
        rate_pct=rate_pct,
        label=f"¥{min_amount:,.0f}-¥{max_amount:,.0f}",
        confidence=_resolve_confidence(input.compensation_signal),
        rule_version=RULE_VERSION,
    )


def _resolve_salary_band(category: str, seniority: str) -> tuple[int, int]:
    category_bands = DEFAULT_ANNUAL_SALARY_BANDS.get(category) or DEFAULT_ANNUAL_SALARY_BANDS["技术"]
    return category_bands.get(seniority) or category_bands["none"]


def _resolve_fee_rate_pct(input: BountyEstimateInput) -> int:
    rate = 12
    if input.hard_to_fill:
        rate += 3
    if input.critical:
        rate += 2
    if input.role_complexity == "high":
        rate += 1
    if input.business_criticality == "high":
        rate += 1
    if input.urgent:
        rate += 1
    if "long_running" in input.time_pressure_signals:
        rate += 1
    if input.company_signal == "hot":
        rate += 1
    return max(10, min(rate, 20))


def _resolve_confidence(compensation_signal: str) -> str:
    if compensation_signal == "strong":
        return "high"
    return "medium"
