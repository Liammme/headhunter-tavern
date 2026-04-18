from dataclasses import dataclass

RULE_VERSION = "score-v1"


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
