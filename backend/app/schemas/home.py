from typing import Literal

from pydantic import BaseModel, Field


class VerificationTagOut(BaseModel):
    label: str
    tone: Literal["positive", "warning", "danger", "neutral"]
    description: str


class JobCardOut(BaseModel):
    id: int
    title: str
    canonical_url: str
    bounty_grade: str
    tags: list[str]
    verification_tags: list[VerificationTagOut] = Field(default_factory=list)
    claimed_names: list[str]


class JdTrustOut(BaseModel):
    legacy_job_id: int
    canonical_url: str | None = None
    source_name: str | None = None
    title: str | None = None
    company: str | None = None
    risk_level: Literal["low", "needs_review", "high"]
    trust_score: int | None = None
    reason_codes: list[str]
    recommended_checks: list[str]
    evidence_refs: list[str]
    domain_warnings: list[dict] = Field(default_factory=list)
    verification_tags: list[VerificationTagOut] = Field(default_factory=list)


class CompanyCardOut(BaseModel):
    company: str
    company_url: str | None = None
    company_grade: str
    total_jobs: int
    claimed_names: list[str]
    jobs: list[JobCardOut]
    claimed_by: str | None = None
    claim_status: str | None = None
    estimated_bounty_amount: int | None = None
    estimated_bounty_label: str | None = None
    jd_trust: JdTrustOut | None = None


class DayBucketOut(BaseModel):
    bucket: Literal["within_3_days", "within_7_days", "earlier"]
    companies: list[CompanyCardOut]


class IntelligenceOut(BaseModel):
    narrative: str
    headline: str
    summary: str
    analysis_version: str
    rule_version: str
    window_start: str | None
    window_end: str
    generated_at: str
    findings: list[str]
    actions: list[str]
    living_report: dict | None = None


class HomeMetaOut(BaseModel):
    analysis_version: str
    rule_version: str
    window_start: str
    window_end: str
    generated_at: str


class HomePayload(BaseModel):
    intelligence: IntelligenceOut
    meta: HomeMetaOut
    days: list[DayBucketOut]
