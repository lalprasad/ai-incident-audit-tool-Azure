from __future__ import annotations

import re

from app.audit.scoring_engine import ScoringEngine
from app.models.llm import EvidenceItem, LlmAuditEvaluation, MeasureEvaluation
from app.models.ticket import IncidentTicket
from app.utils.errors import ScoringError

MIN_QUOTE_LENGTH = 12


def ticket_corpus(ticket: IncidentTicket) -> str:
    parts: list[str] = []

    def add(value: object) -> None:
        if isinstance(value, str) and value.strip():
            parts.append(value)
        elif isinstance(value, list):
            for item in value:
                add(item)
        elif isinstance(value, dict):
            for nested in value.values():
                add(nested)

    add(ticket.model_dump(mode="json"))
    return "\n".join(parts)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def quote_supported(quote: str, corpus: str) -> bool:
    if not quote or len(quote.strip()) < MIN_QUOTE_LENGTH:
        return False
    return _normalize(quote) in _normalize(corpus)


class EvidenceAnalyzer:
    """Reject invented quotes. The scoring engine still owns the numeric range."""

    def __init__(self, scoring: ScoringEngine) -> None:
        self._scoring = scoring

    def validate(self, evaluation: LlmAuditEvaluation, ticket: IncidentTicket) -> LlmAuditEvaluation:
        corpus = ticket_corpus(ticket)
        measures: list[MeasureEvaluation] = []
        flags = list(evaluation.flags)
        for measure in evaluation.measures:
            self._scoring.validate_measure_score(measure.measure_id, measure.score)
            evidence, unsupported = self._check_evidence(measure.evidence, corpus, ticket)
            confidence = measure.confidence
            if unsupported:
                if "unsupported evidence" not in flags:
                    flags.append("unsupported evidence")
                confidence = min(confidence, 0.5)
            if evidence and not any(item.evidence_status == "Supported" for item in evidence):
                if "insufficient evidence" not in flags:
                    flags.append("insufficient evidence")
            measures.append(measure.model_copy(update={"evidence": evidence, "confidence": confidence}))
        return evaluation.model_copy(update={"measures": measures, "flags": flags})

    def _check_evidence(
        self,
        evidence: list[EvidenceItem],
        corpus: str,
        ticket: IncidentTicket,
    ) -> tuple[list[EvidenceItem], int]:
        checked: list[EvidenceItem] = []
        unsupported = 0
        for item in evidence:
            if not item.text.strip() or not item.relevance.strip() or not item.ticket_field.strip():
                unsupported += 1
                checked.append(self._rejected("Evidence item did not meet the evidence schema."))
                continue
            timestamp = item.timestamp
            page = item.page
            if timestamp and timestamp not in corpus:
                timestamp = None
                unsupported += 1
            if page is not None and ticket.source_pages and page not in ticket.source_pages:
                page = None
                unsupported += 1
            if item.evidence_status == "Insufficient evidence":
                checked.append(item.model_copy(update={"timestamp": timestamp, "page": page}))
                continue
            if quote_supported(item.text, corpus):
                checked.append(item.model_copy(update={"timestamp": timestamp, "page": page}))
                continue
            unsupported += 1
            checked.append(self._rejected("The model supplied a quote that is not present in the ticket."))
        return checked, unsupported

    def _rejected(self, relevance: str) -> EvidenceItem:
        return EvidenceItem(
            text="Insufficient evidence.",
            source_section="system",
            ticket_field="system",
            relevance=relevance,
            evidence_status="Insufficient evidence",
        )


def assert_score_or_raise(scoring: ScoringEngine, measure_id: str, score: int) -> None:
    try:
        scoring.validate_measure_score(measure_id, score)
    except ScoringError:
        raise
