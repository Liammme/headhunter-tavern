from dataclasses import asdict, dataclass

from app.services.job_facts import JobFacts
from app.services.scoring import JobScoreInput, JobScoreResult, JobScoreV2Input, JobScoreV2Result


@dataclass(frozen=True)
class ScoringComparisonSnapshot:
    title: str
    facts: dict
    v1_input: dict
    v1_result: dict
    v2_input: dict
    v2_result: dict
    summary: dict


def build_comparison_snapshot(
    *,
    facts: JobFacts,
    v1_input: JobScoreInput,
    v1_result: JobScoreResult,
    v2_input: JobScoreV2Input,
    v2_result: JobScoreV2Result,
) -> ScoringComparisonSnapshot:
    return ScoringComparisonSnapshot(
        title=facts.title,
        facts=asdict(facts),
        v1_input=asdict(v1_input),
        v1_result=asdict(v1_result),
        v2_input=asdict(v2_input),
        v2_result={
            **asdict(v2_result),
            "rule_hits": [asdict(rule_hit) for rule_hit in v2_result.rule_hits],
        },
        summary=build_difference_summary(facts=facts, v1_result=v1_result, v2_result=v2_result),
    )


def build_difference_summary(
    *,
    facts: JobFacts,
    v1_result: JobScoreResult,
    v2_result: JobScoreV2Result,
) -> dict:
    notes: list[str] = []
    if v1_result.grade != v2_result.grade:
        if not facts.time_pressure_signals and not facts.anomaly_signals and grade_rank(v1_result.grade) > grade_rank(v2_result.grade):
            notes.append("v2 因缺少时间压力或招聘异常信号而更保守")
        if facts.time_pressure_signals or facts.anomaly_signals:
            notes.append("v2 更强调时间压力和招聘异常带来的介入优先级")
    if facts.bd_entry:
        notes.append("v2 保留了 BD 切入口价值，不只看产研关键词")
    if not notes:
        notes.append("v1/v2 对该岗位的优先级判断基本一致")

    return {
        "grade_changed": v1_result.grade != v2_result.grade,
        "score_delta": v2_result.score - v1_result.score,
        "difference_notes": notes,
    }


def grade_rank(grade: str) -> int:
    return {"low": 0, "medium": 1, "high": 2}.get(grade, -1)
