from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

JobStatus = Literal[
    "Uploaded",
    "Extracting",
    "Tickets identified",
    "Auditing",
    "Completed",
    "Failed",
]


class AuditJob(BaseModel):
    id: str
    filename: str
    blob_name: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    error: str | None = None
    ticket_ids: list[str] = Field(default_factory=list)
    audit_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    stage_timings_ms: dict[str, int] = Field(default_factory=dict)
    stages: list[str] = Field(
        default_factory=lambda: [
            "Uploaded",
            "Extracting",
            "Tickets identified",
            "Auditing",
            "Completed",
        ]
    )


class JobList(BaseModel):
    items: list[AuditJob]
    total: int
