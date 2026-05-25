from pydantic import BaseModel, Field


class TalentversePageInfo(BaseModel):
    limit: int
    nextCursor: str | None = None


class TalentverseReportListResponse(BaseModel):
    items: list[dict] = Field(default_factory=list)
    pageInfo: TalentversePageInfo
