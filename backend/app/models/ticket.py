from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TimelineEvent(BaseModel):
    timestamp: datetime | None = None
    author: str | None = None
    event_type: str
    text: str
    audience: Literal["customer", "internal", "unknown"] = "unknown"


class IncidentTicket(BaseModel):
    ticket_id: str | None = None
    short_description: str | None = None
    description: str | None = None
    priority: str | None = None
    severity: str | None = None
    assignment_group: str | None = None
    assigned_to: str | None = None
    caller: str | None = None
    business_service: str | None = None
    configuration_item: str | None = None
    opened_at: datetime | None = None
    updated_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    state: str | None = None
    work_notes: str | None = None
    additional_comments: str | None = None
    resolution_notes: str | None = None
    resolution_code: str | None = None
    cause: str | None = None
    close_notes: str | None = None
    raw_text: str = ""
    source_pages: list[int] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)

    def llm_payload(self) -> dict:
        """Fields that may be sent to a model. Raw PDF bytes are never included."""

        payload = self.model_dump(mode="json", exclude={"raw_text"})
        return payload


class RawSegment(BaseModel):
    raw_text: str
    source_pages: list[int] = Field(default_factory=list)
    fields: dict[str, str] = Field(default_factory=dict)


class PageText(BaseModel):
    number: int
    text: str
    tables: list[list[list[str]]] = Field(default_factory=list)
    key_values: dict[str, str] = Field(default_factory=dict)


class DocumentExtraction(BaseModel):
    pages: list[PageText]
    warnings: list[str] = Field(default_factory=list)
