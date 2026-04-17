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
    company_grade: str
    total_jobs: int
    claimed_names: list[str]
    jobs: list[JobCardOut]


class DayBucketOut(BaseModel):
    bucket: str
    companies: list[CompanyCardOut]


class IntelligenceOut(BaseModel):
    headline: str
    summary: str
    findings: list[str]
    actions: list[str]


class HomePayload(BaseModel):
    intelligence: IntelligenceOut
    days: list[DayBucketOut]
