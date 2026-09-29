from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.llm import EvidenceItem
from app.models.ticket import IncidentTicket


class MeasureResult(BaseModel):
    measure_id: str
    measure_name: str
    ai_score: int
    auditor_score: int | None = None
    final_score: int
    auditor_comments: str | None = None
    override_reason: str | None = None
    overridden: bool = False
    confidence: float
    confidence_label: str
    evidence: list[EvidenceItem]
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    recommendation: str
    ai_score_is_system_extension: bool = False
    final_score_is_system_extension: bool = False
    guidance: str = ""


class AuditorReview(BaseModel):
    decision: str
    comments: str | None = None
    reviewed_at: datetime


class AuditRecord(BaseModel):
    id: str
    ticket_id: str
    audit_version: int
    audited_at: datetime
    job_id: str
    overall_score: float
    maximum_score: float
    percentage: float
    classification: str
    totals_computed_by: str = "scoring_engine"
    ai_model: str
    criteria_version: str
    prompt_version: str
    model_version: str
    measures: list[MeasureResult]
    human_review_required: bool
    review_reasons: list[str] = Field(default_factory=list)
    auditor_override: bool = False
    auditor_review: AuditorReview | None = None
    overall_strengths: list[str] = Field(default_factory=list)
    overall_gaps: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    ticket: IncidentTicket


class AuditSummary(BaseModel):
    id: str
    ticket_id: str
    audit_version: int
    audited_at: datetime
    job_id: str
    overall_score: float
    maximum_score: float
    percentage: float
    classification: str
    human_review_required: bool
    auditor_override: bool
    short_description: str | None = None
    priority: str | None = None
    state: str | None = None
    opened_at: datetime | None = None


class AuditList(BaseModel):
    items: list[AuditSummary]
    total: int
