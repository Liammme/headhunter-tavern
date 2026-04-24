from dataclasses import dataclass

from app.services.job_facts import JobFacts, build_v1_score_input, build_v2_score_input
from app.services.scoring import score_job, score_job_v2
from app.services.scoring_comparison import ScoringComparisonSnapshot, build_comparison_snapshot


@dataclass(frozen=True)
class ScoringSampleCase:
    sample_id: str
    label: str
    facts: JobFacts


@dataclass(frozen=True)
class ScoringSampleResult:
    sample_id: str
    label: str
    difference_kind: str
    snapshot: ScoringComparisonSnapshot


def build_scoring_sample_suite() -> list[ScoringSampleResult]:
    results: list[ScoringSampleResult] = []
    for case in build_sample_cases():
        v1_input = build_v1_score_input(case.facts)
        v2_input = build_v2_score_input(case.facts)
        v1_result = score_job(v1_input)
        v2_result = score_job_v2(v2_input)
        snapshot = build_comparison_snapshot(
            facts=case.facts,
            v1_input=v1_input,
            v1_result=v1_result,
            v2_input=v2_input,
            v2_result=v2_result,
        )
        results.append(
            ScoringSampleResult(
                sample_id=case.sample_id,
                label=case.label,
                difference_kind=classify_difference_kind(v1_result["grade"] if isinstance(v1_result, dict) else v1_result.grade,
                                                         v2_result["grade"] if isinstance(v2_result, dict) else v2_result.grade),
                snapshot=snapshot,
            )
        )
    return results


def build_sample_cases() -> list[ScoringSampleCase]:
    return [
        ScoringSampleCase(
            sample_id="principal-ai-no-pressure",
            label="高级产研岗但无时间压力",
            facts=JobFacts(
                title="Principal AI Engineer",
                category="AI/算法",
                domain_tag="AI",
                seniority="principal",
                urgent=False,
                critical=True,
                bd_entry=False,
                hard_to_fill=True,
                role_complexity="high",
                business_criticality="medium",
                anomaly_signals=(),
                compensation_signal="unknown",
                company_signal="hot",
                time_pressure_signals=(),
            ),
        ),
        ScoringSampleCase(
            sample_id="urgent-backend-anomaly",
            label="急招且有异常信号的关键岗位",
            facts=JobFacts(
                title="Backend Engineer",
                category="技术",
                domain_tag="工具/SaaS",
                seniority="none",
                urgent=True,
                critical=False,
                bd_entry=False,
                hard_to_fill=False,
                role_complexity="medium",
                business_criticality="high",
                anomaly_signals=("long_running", "wish_list_jd"),
                compensation_signal="unknown",
                company_signal="neutral",
                time_pressure_signals=("urgent", "long_running"),
            ),
        ),
        ScoringSampleCase(
            sample_id="bd-manager-entry-point",
            label="BD 切入口强但非产研核心",
            facts=JobFacts(
                title="Business Development Manager",
                category="商务",
                domain_tag="Web3",
                seniority="senior",
                urgent=True,
                critical=False,
                bd_entry=True,
                hard_to_fill=False,
                role_complexity="medium",
                business_criticality="high",
                anomaly_signals=(),
                compensation_signal="unknown",
                company_signal="hot",
                time_pressure_signals=("urgent",),
            ),
        ),
        ScoringSampleCase(
            sample_id="ops-general-low-priority",
            label="普通低优先级岗位",
            facts=JobFacts(
                title="Operations Coordinator",
                category="运营",
                domain_tag="工具/SaaS",
                seniority="none",
                urgent=False,
                critical=False,
                bd_entry=False,
                hard_to_fill=False,
                role_complexity="low",
                business_criticality="low",
                anomaly_signals=(),
                compensation_signal="unknown",
                company_signal="neutral",
                time_pressure_signals=(),
            ),
        ),
        ScoringSampleCase(
            sample_id="founding-pm-boundary",
            label="边界岗位",
            facts=JobFacts(
                title="Founding Product Lead",
                category="产品",
                domain_tag="AI",
                seniority="lead",
                urgent=True,
                critical=True,
                bd_entry=True,
                hard_to_fill=False,
                role_complexity="high",
                business_criticality="high",
                anomaly_signals=("wish_list_jd",),
                compensation_signal="strong",
                company_signal="hot",
                time_pressure_signals=("urgent", "founder_hiring"),
            ),
        ),
    ]


def classify_difference_kind(v1_grade: str, v2_grade: str) -> str:
    if v1_grade == "high" and v2_grade == "medium":
        return "v1_high_to_v2_medium"
    if v1_grade == "medium" and v2_grade == "high":
        return "v1_medium_to_v2_high"
    if v1_grade == v2_grade:
        return "aligned"
    return "changed_other"


def format_sample_summaries(samples: list[ScoringSampleResult]) -> list[str]:
    lines: list[str] = []
    for sample in samples:
        first_reason = sample.snapshot.v2_result["reasons"][0] if sample.snapshot.v2_result["reasons"] else "无"
        lines.append(
            f"{sample.snapshot.title}: {sample.snapshot.v1_result['grade']} -> {sample.snapshot.v2_result['grade']} | {first_reason}"
        )
    return lines
