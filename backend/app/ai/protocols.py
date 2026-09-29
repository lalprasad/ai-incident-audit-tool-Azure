from __future__ import annotations

from typing import Protocol

from app.models.criteria import AuditCriteria
from app.models.llm import LlmAuditEvaluation
from app.models.ticket import DocumentExtraction, IncidentTicket


class DocumentClient(Protocol):
    async def analyze(self, content: bytes, filename: str) -> DocumentExtraction:
        """Extract text, tables, and key values from a PDF."""


class AuditModel(Protocol):
    async def evaluate(
        self,
        ticket: IncidentTicket,
        criteria: AuditCriteria,
        system_prompt: str,
        user_prompt: str,
    ) -> LlmAuditEvaluation:
        """Return per-measure scores and evidence. Totals are ignored."""


class CriteriaRetriever(Protocol):
    def get_criteria(self) -> AuditCriteria:
        """Load the rubric. Azure AI Search can replace the local file later."""
