from __future__ import annotations

from app.ai.mock_rules import evaluate_ticket
from app.models.criteria import AuditCriteria
from app.models.llm import LlmAuditEvaluation
from app.models.ticket import IncidentTicket


class MockAuditModel:
    """Schema-valid evaluations from ticket text. Totals are left empty on purpose."""

    async def evaluate(
        self,
        ticket: IncidentTicket,
        criteria: AuditCriteria,
        system_prompt: str,
        user_prompt: str,
    ) -> LlmAuditEvaluation:
        del system_prompt, user_prompt
        return evaluate_ticket(ticket, criteria)
