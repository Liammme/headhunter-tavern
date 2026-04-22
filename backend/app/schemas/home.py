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


class DayBucketOut(BaseModel):
    bucket: str
    companies: list[CompanyCardOut]


class IntelligenceOut(BaseModel):
    narrative: str
    headline: str
    summary: str
    analysis_version: str
    rule_version: str
    window_start: str
    window_end: str
    generated_at: str
    findings: list[str]
    actions: list[str]


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
