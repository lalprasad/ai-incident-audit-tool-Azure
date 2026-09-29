from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import get_container
from app.models.audit import AuditRecord
from app.services.container import Container

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


class OverrideRequest(BaseModel):
    auditor_score: int = Field(ge=1, le=5)
    auditor_comments: str = ""
    override_reason: str


class ReviewRequest(BaseModel):
    decision: Literal["accept", "comment"]
    comments: str = ""


@router.get("/{ticket_id}", response_model=AuditRecord)
def get_ticket(ticket_id: str, container: Container = Depends(get_container)) -> AuditRecord:
    return container.audits.latest_for_ticket(ticket_id)


@router.post("/{ticket_id}/review", response_model=AuditRecord)
def review_ticket(
    ticket_id: str,
    body: ReviewRequest,
    container: Container = Depends(get_container),
) -> AuditRecord:
    return container.audits.review_ticket(ticket_id, decision=body.decision, comments=body.comments)


@router.put("/{ticket_id}/measures/{measure_id}", response_model=AuditRecord)
def override_measure(
    ticket_id: str,
    measure_id: str,
    body: OverrideRequest,
    container: Container = Depends(get_container),
) -> AuditRecord:
    return container.audits.override_measure(
        ticket_id,
        measure_id,
        auditor_score=body.auditor_score,
        auditor_comments=body.auditor_comments,
        override_reason=body.override_reason,
    )
