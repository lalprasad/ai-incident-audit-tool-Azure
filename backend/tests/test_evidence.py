import pytest
from pydantic import ValidationError

from app.audit.evidence_analyzer import EvidenceAnalyzer, quote_supported, ticket_corpus
from app.audit.scoring_engine import ScoringEngine
from app.models.criteria import AuditCriteria
from app.models.llm import EvidenceItem, LlmAuditEvaluation, MeasureEvaluation
from app.models.ticket import IncidentTicket


def _evaluation(evidence: list[EvidenceItem], score: int = 4) -> LlmAuditEvaluation:
    def measure(measure_id: str, name: str, item_score: int, items: list[EvidenceItem]) -> MeasureEvaluation:
        return MeasureEvaluation(
            measure_id=measure_id,
            measure_name=name,
            score=item_score,
            confidence=0.9,
            evidence=items,
            recommendation="Document the missing fact from the ticket.",
        )

    return LlmAuditEvaluation(
        ticket_id="INC1",
        measures=[
            measure("user_engagement", "User Engagement & Investigation Handling", score, evidence),
            measure("issue_diagnosis", "Issue Diagnosis", score, evidence),
            measure("solutioning", "Solutioning", score, evidence),
        ],
        percentage=1,
        overall_score=1,
        classification="Needs Improvement",
    )


def test_supported_quote_must_appear_in_the_ticket(criteria: AuditCriteria) -> None:
    ticket = IncidentTicket(
        ticket_id="INC1",
        description="Pipeline failed.",
        source_pages=[2],
    )
    analyzer = EvidenceAnalyzer(ScoringEngine(criteria))
    invented = EvidenceItem(
        text="Priya Nair patched the cluster at 02:00.",
        source_section="resolution_notes",
        ticket_field="resolution_notes",
        relevance="Invented owner and timestamp.",
        timestamp="1999-01-01 00:00",
        page=9,
    )
    real = EvidenceItem(
        text="Pipeline failed.",
        source_section="description",
        ticket_field="description",
        relevance="Symptom only.",
        page=2,
    )
    result = analyzer.validate(_evaluation([invented, real]), ticket)
    statuses = [item.evidence_status for item in result.measures[0].evidence]
    assert statuses[0] == "Insufficient evidence"
    assert "Priya Nair" not in result.measures[0].evidence[0].text
    assert result.measures[0].evidence[0].timestamp is None
    assert result.measures[0].evidence[0].page is None
    assert result.measures[0].evidence[1].evidence_status == "Supported"
    assert result.measures[0].evidence[1].text == "Pipeline failed."
    assert "unsupported evidence" in result.flags
    assert result.percentage == 1


def test_insufficient_evidence_does_not_need_a_quote(criteria: AuditCriteria) -> None:
    ticket = IncidentTicket(ticket_id="INC1", description="Users cannot send email.")
    item = EvidenceItem(
        text="Root cause not sufficiently documented.",
        source_section="cause",
        ticket_field="cause",
        relevance="The ticket does not contain enough information to support a higher score.",
        evidence_status="Insufficient evidence",
    )
    result = EvidenceAnalyzer(ScoringEngine(criteria)).validate(_evaluation([item], score=1), ticket)
    assert result.measures[0].evidence[0].evidence_status == "Insufficient evidence"
    assert result.measures[0].evidence[0].text == "Root cause not sufficiently documented."


def test_quote_helper_rejects_short_or_missing_text() -> None:
    corpus = ticket_corpus(IncidentTicket(ticket_id="INC1", description="Pipeline failed."))
    assert quote_supported("Pipeline failed.", corpus)
    assert not quote_supported("failed", corpus)
    assert not quote_supported("root cause was a bad deploy", corpus)


def test_schema_rejects_scores_outside_the_range() -> None:
    with pytest.raises(ValidationError):
        MeasureEvaluation(
            measure_id="user_engagement",
            measure_name="User Engagement & Investigation Handling",
            score=9,
            confidence=0.4,
            evidence=[],
            recommendation="Add updates.",
        )


def test_confidence_above_one_is_rejected() -> None:
    with pytest.raises(ValidationError):
        MeasureEvaluation(
            measure_id="issue_diagnosis",
            measure_name="Issue Diagnosis",
            score=3,
            confidence=1.2,
            evidence=[],
            recommendation="Document the root cause.",
        )
