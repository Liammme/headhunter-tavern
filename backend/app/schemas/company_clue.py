from typing import Literal

from pydantic import BaseModel, Field


class CompanyClueRequest(BaseModel):
    company: str = Field(min_length=1, max_length=256)


class CompanyClueSection(BaseModel):
    key: str
    title: str
    content: str


class CompanyClueResponse(BaseModel):
    status: Literal["loading", "success", "failure"]
    company: str
    generated_at: str
    narrative: str
    sections: list[CompanyClueSection]
    error_message: str | None = None
