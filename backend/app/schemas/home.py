from typing import Literal

from pydantic import BaseModel


class JobCardOut(BaseModel):
    id: int
    title: str
    canonical_url: str
    bounty_grade: str
    tags: list[str]
    claimed_names: list[str]


class CompanyCardOut(BaseModel):
    company: str
    company_url: str | None = None
    company_grade: str
    total_jobs: int
    claimed_names: list[str]
    jobs: list[JobCardOut]
    claimed_by: str | None = None
    claim_status: str | None = None


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
