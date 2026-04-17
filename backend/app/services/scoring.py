def derive_job_grade(title: str, category: str, signals: dict) -> str:
    score = 0
    lowered = (title or "").lower()

    if any(keyword in lowered for keyword in ("senior", "lead", "staff", "head", "principal", "architect")):
        score += 2
    if category in {"技术", "AI/算法", "数据", "产品"}:
        score += 2
    if signals.get("urgent"):
        score += 2
    if signals.get("critical"):
        score += 2
    if signals.get("bd_entry"):
        score += 1

    if score >= 6:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


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
