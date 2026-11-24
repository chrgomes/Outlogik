import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Section = Literal["traffic", "ai", "search", "audit"]


class ReportIn(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    sections: list[Section] = Field(min_length=1, max_length=4)
    days: int | None = Field(default=None, ge=1, le=486)
    start: date | None = None
    end: date | None = None
    compare: Literal["previous", "year", "none"] = "previous"


class SourceOut(BaseModel):
    name: str
    detail: str
    through: date | None


class CsvFileOut(BaseModel):
    name: str
    label: str


class ReportOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    workspace_name: str
    title: str
    sections: list[Section]
    period_start: date
    period_end: date
    compare: Literal["previous", "year", "none"]
    compare_start: date | None
    compare_end: date | None
    sources: list[SourceOut]
    unavailable: list[str]
    csv_files: list[CsvFileOut]
    created_at: datetime
    created_by: str | None
