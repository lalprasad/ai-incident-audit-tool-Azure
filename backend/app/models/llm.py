from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    text: str
    source_section: str
    ticket_field: str
    relevance: str
    evidence_status: Literal["Supported", "Insufficient evidence"] = "Supported"
    timestamp: str | None = None
    page: int | None = None


class MeasureEvaluation(BaseModel):
    measure_id: str
    measure_name: str
    score: int = Field(ge=1, le=5)
    confidence: float = Field(ge=0, le=1)
    evidence: list[EvidenceItem]
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    recommendation: str


class LlmAuditEvaluation(BaseModel):
    """Structured model output. Totals on this object are not authoritative."""

    ticket_id: str | None = None
    measures: list[MeasureEvaluation]
    overall_strengths: list[str] = Field(default_factory=list)
    overall_gaps: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    overall_score: float | None = None
    maximum_score: float | None = None
    percentage: float | None = None
    classification: str | None = None
    token_usage: dict[str, int] | None = None
    latency_ms: int | None = None
