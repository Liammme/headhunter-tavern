from pydantic import BaseModel


class BdContactItem(BaseModel):
    id: int
    company: str
    companyNormalized: str
    jobTitle: str
    contactType: str
    contactValue: str
    confidence: str
    region: str
    sourceName: str
    jobUrl: str
    companyUrl: str | None
    evidenceSnippet: str
    firstSeenAt: str
    lastSeenAt: str
    status: str


class BdContactPageInfo(BaseModel):
    limit: int
    offset: int
    count: int


class BdContactListResponse(BaseModel):
    region: str
    items: list[BdContactItem]
    pageInfo: BdContactPageInfo
