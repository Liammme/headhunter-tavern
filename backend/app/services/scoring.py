from dataclasses import dataclass

RULE_VERSION = "score-v1"
RULE_VERSION_V2 = "score-v2"
V2_HIGH_THRESHOLD = 75
V2_MEDIUM_THRESHOLD = 45


@dataclass(frozen=True)
class JobScoreInput:
    title: str
    category: str
    urgent: bool
    critical: bool
    bd_entry: bool


@dataclass(frozen=True)
class JobScoreResult:
    score: int
    grade: str


@dataclass(frozen=True)
class ScoreRuleHit:
    code: str
    dimension: str
    weight: int


@dataclass(frozen=True)
class JobScoreV2Input:
    seniority: str
    urgent: bool
    critical: bool
    bd_entry: bool
    hard_to_fill: bool
    role_complexity: str
    business_criticality: str
    anomaly_signals: tuple[str, ...]
    category: str
    domain_tag: str
    compensation_signal: str
    company_signal: str
    time_pressure_signals: tuple[str, ...] = ()


@dataclass(frozen=True)
class JobScoreV2Result:
    score: int
    grade: str
    rule_version: str
    reasons: tuple[str, ...]
    rule_hits: tuple[ScoreRuleHit, ...]


def score_job_v2(input_data: JobScoreV2Input) -> JobScoreV2Result:
    rule_hits: list[ScoreRuleHit] = []

    add_v2_rule_hits(rule_hits, score_v2_time_pressure(input_data))
    add_v2_rule_hits(rule_hits, score_v2_hard_to_fill(input_data))
    add_v2_rule_hits(rule_hits, score_v2_business_criticality(input_data))
    add_v2_rule_hits(rule_hits, score_v2_anomaly_signals(input_data))
    add_v2_rule_hits(rule_hits, score_v2_modifiers(input_data))

    score = sum(hit.weight for hit in rule_hits)
    if should_cap_v2_high_grade(input_data, rule_hits) and score >= V2_HIGH_THRESHOLD:
        score = V2_HIGH_THRESHOLD - 1
        rule_hits.append(
            ScoreRuleHit(code="guardrail.no_pressure_or_anomaly_cap", dimension="guardrail", weight=0)
        )

    grade = classify_v2_grade(score)
    reasons = build_v2_reasons(input_data, rule_hits)
    return JobScoreV2Result(
        score=score,
        grade=grade,
        rule_version=RULE_VERSION_V2,
        reasons=reasons,
        rule_hits=tuple(rule_hits),
    )


def score_job(input_data: JobScoreInput) -> JobScoreResult:
    score = 0
    lowered = (input_data.title or "").lower()

    if any(keyword in lowered for keyword in ("senior", "lead", "staff", "head", "principal", "architect")):
        score += 2
    if input_data.category in {"技术", "AI/算法", "数据", "产品"}:
        score += 2
    if input_data.urgent:
        score += 2
    if input_data.critical:
        score += 2
    if input_data.bd_entry:
        score += 1

    if score >= 6:
        return JobScoreResult(score=score, grade="high")
    if score >= 3:
        return JobScoreResult(score=score, grade="medium")
    return JobScoreResult(score=score, grade="low")


def derive_job_grade(title: str, category: str, signals: dict) -> str:
    return score_job(
        JobScoreInput(
            title=title,
            category=category,
            urgent=bool(signals.get("urgent")),
            critical=bool(signals.get("critical")),
            bd_entry=bool(signals.get("bd_entry")),
        )
    ).grade


def derive_company_grade(job_grades: list[str]) -> str:
    counts = {"high": 0, "medium": 0, "low": 0}
    grade_priority = {"high": 0, "medium": 1, "low": 2}

    for grade in job_grades:
        if grade not in counts:
            continue
        counts[grade] += 1

    max_count = max(counts.values(), default=0)
    if max_count == 0:
        return "normal"

    tied_grades = [grade for grade, count in counts.items() if count == max_count]
    majority = min(tied_grades, key=lambda grade: grade_priority[grade])
    if len(tied_grades) > 1:
        majority = max(tied_grades, key=lambda grade: grade_priority[grade])

    return {"high": "focus", "medium": "watch", "low": "normal"}[majority]


def score_v2_time_pressure(input_data: JobScoreV2Input) -> tuple[ScoreRuleHit, ...]:
    hits: list[ScoreRuleHit] = []
    if input_data.urgent:
        hits.append(ScoreRuleHit(code="time_pressure.urgent", dimension="time_pressure", weight=18))
    if "founder_hiring" in input_data.time_pressure_signals:
        hits.append(ScoreRuleHit(code="time_pressure.founder_hiring", dimension="time_pressure", weight=8))
    if "long_running" in input_data.time_pressure_signals:
        hits.append(ScoreRuleHit(code="time_pressure.long_running", dimension="time_pressure", weight=10))
    return tuple(hits)


def score_v2_hard_to_fill(input_data: JobScoreV2Input) -> tuple[ScoreRuleHit, ...]:
    hits: list[ScoreRuleHit] = []
    if input_data.hard_to_fill:
        hits.append(ScoreRuleHit(code="hard_to_fill.market_supply", dimension="hard_to_fill", weight=16))

    seniority_weights = {
        "vp": 10,
        "director": 10,
        "head": 10,
        "principal": 9,
        "staff": 9,
        "architect": 8,
        "lead": 7,
        "senior": 4,
        "founding": 8,
    }
    seniority_weight = seniority_weights.get(input_data.seniority, 0)
    if seniority_weight:
        hits.append(ScoreRuleHit(code=f"hard_to_fill.seniority.{input_data.seniority}", dimension="hard_to_fill", weight=seniority_weight))

    complexity_weights = {"high": 8, "medium": 4, "low": 0}
    complexity_weight = complexity_weights.get(input_data.role_complexity, 0)
    if complexity_weight:
        hits.append(
            ScoreRuleHit(
                code=f"hard_to_fill.role_complexity.{input_data.role_complexity}",
                dimension="hard_to_fill",
                weight=complexity_weight,
            )
        )
    return tuple(hits)


def score_v2_business_criticality(input_data: JobScoreV2Input) -> tuple[ScoreRuleHit, ...]:
    hits: list[ScoreRuleHit] = []
    criticality_weights = {"high": 18, "medium": 10, "low": 0}
    criticality_weight = criticality_weights.get(input_data.business_criticality, 0)
    if criticality_weight:
        hits.append(
            ScoreRuleHit(
                code=f"business_criticality.{input_data.business_criticality}",
                dimension="business_criticality",
                weight=criticality_weight,
            )
        )
    if input_data.critical:
        hits.append(ScoreRuleHit(code="business_criticality.critical_role", dimension="business_criticality", weight=6))
    return tuple(hits)


def score_v2_anomaly_signals(input_data: JobScoreV2Input) -> tuple[ScoreRuleHit, ...]:
    weights = {
        "reposted": 10,
        "wish_list_jd": 10,
        "long_running": 8,
    }
    hits: list[ScoreRuleHit] = []
    for signal in input_data.anomaly_signals:
        weight = weights.get(signal, 0)
        if weight:
            hits.append(ScoreRuleHit(code=f"anomaly.{signal}", dimension="anomaly", weight=weight))
    return tuple(hits)


def score_v2_modifiers(input_data: JobScoreV2Input) -> tuple[ScoreRuleHit, ...]:
    hits: list[ScoreRuleHit] = []
    if input_data.bd_entry:
        hits.append(ScoreRuleHit(code="bd_entry.role", dimension="bd_entry", weight=8))

    category_weights = {
        "AI/算法": 6,
        "数据": 5,
        "技术": 5,
        "产品": 4,
    }
    category_weight = category_weights.get(input_data.category, 0)
    if category_weight:
        hits.append(ScoreRuleHit(code=f"category_bias.{input_data.category}", dimension="category_bias", weight=category_weight))

    if input_data.compensation_signal == "strong":
        hits.append(ScoreRuleHit(code="compensation.strong", dimension="compensation", weight=3))
    if input_data.company_signal == "hot":
        hits.append(ScoreRuleHit(code="company_signal.hot", dimension="company_signal", weight=3))
    return tuple(hits)


def add_v2_rule_hits(rule_hits: list[ScoreRuleHit], hits: tuple[ScoreRuleHit, ...]) -> None:
    rule_hits.extend(hits)


def should_cap_v2_high_grade(input_data: JobScoreV2Input, rule_hits: list[ScoreRuleHit]) -> bool:
    has_time_pressure = any(hit.dimension == "time_pressure" for hit in rule_hits)
    has_anomaly = any(hit.dimension == "anomaly" for hit in rule_hits)
    return not has_time_pressure and not has_anomaly and not input_data.urgent


def classify_v2_grade(score: int) -> str:
    if score >= V2_HIGH_THRESHOLD:
        return "high"
    if score >= V2_MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def build_v2_reasons(input_data: JobScoreV2Input, rule_hits: list[ScoreRuleHit]) -> tuple[str, ...]:
    reasons: list[str] = []
    if any(hit.dimension == "time_pressure" for hit in rule_hits):
        reasons.append("时间压力高，适合猎头优先介入")
    if any(hit.dimension == "hard_to_fill" for hit in rule_hits):
        reasons.append("岗位难招，公开投递替代性较低")
    if any(hit.dimension == "business_criticality" for hit in rule_hits):
        reasons.append("岗位直接影响业务推进或关键能力建设")
    if any(hit.dimension == "anomaly" for hit in rule_hits):
        reasons.append("存在招聘异常或持续招不动信号")
    if any(hit.dimension == "bd_entry" for hit in rule_hits):
        reasons.append("可作为切入公司关系的 BD 入口")
    if any(hit.dimension == "category_bias" for hit in rule_hits) and input_data.category in {"AI/算法", "数据", "技术", "产品"}:
        reasons.append("产研方向与当前赏金池优先策略一致")
    if not reasons:
        reasons.append("当前岗位缺少明显的优先介入信号")
    return tuple(reasons[:3])
