import asyncio
from pathlib import Path

from app.audit.audit_engine import AuditEngine
from app.audit.evidence_analyzer import EvidenceAnalyzer
from app.audit.scoring_engine import ScoringEngine
from app.audit.timeline_analyzer import TimelineAnalyzer
from app.ai.mock_openai import MockAuditModel
from app.models.criteria import AuditCriteria
from app.models.llm import EvidenceItem, LlmAuditEvaluation, MeasureEvaluation
from app.models.ticket import IncidentTicket

ROOT = Path(__file__).resolve().parents[2]


def _engine(criteria: AuditCriteria, model) -> AuditEngine:
    scoring = ScoringEngine(criteria)
    return AuditEngine(
        model=model,
        scoring=scoring,
        evidence=EvidenceAnalyzer(scoring),
        criteria=criteria,
        timeline=TimelineAnalyzer(),
        system_prompt=(ROOT / "backend/app/ai/prompts/audit_system_prompt.txt").read_text(encoding="utf-8"),
        user_prompt=(ROOT / "backend/app/ai/prompts/audit_user_prompt.txt").read_text(encoding="utf-8"),
        ai_model="test",
        model_version="test",
    )


def test_engine_discards_model_totals(criteria: AuditCriteria, tickets: list[IncidentTicket]) -> None:
    excellent = next(ticket for ticket in tickets if ticket.ticket_id == "INC1001")
    quote = "Acknowledged P2 checkout latency and started the investigation."

    class BiasedModel:
        async def evaluate(self, ticket, rubric, system_prompt, user_prompt):
            del ticket, rubric, system_prompt, user_prompt
            evidence = [
                EvidenceItem(
                    text=quote,
                    source_section="work_notes",
                    ticket_field="work_notes",
                    relevance="Quoted from the ticket.",
                )
            ]
            measures = [
                MeasureEvaluation(
                    measure_id=measure_id,
                    measure_name=name,
                    score=5,
                    confidence=0.95,
                    evidence=evidence,
                    strengths=["Documented in the ticket."],
                    recommendation="Keep the current evidence.",
                )
                for measure_id, name in (
                    ("user_engagement", "User Engagement & Investigation Handling"),
                    ("issue_diagnosis", "Issue Diagnosis"),
                    ("solutioning", "Solutioning"),
                )
            ]
            return LlmAuditEvaluation(
                ticket_id="INC1001",
                measures=measures,
                percentage=1,
                overall_score=1,
                maximum_score=1,
                classification="Needs Improvement",
            )

    record = asyncio.run(
        _engine(criteria, BiasedModel()).audit(
            excellent, job_id="job", version=1, audit_id="audit"
        )
    )
    assert record.percentage == 100
    assert record.overall_score == 15
    assert record.classification == "Excellent"
    assert record.totals_computed_by == "scoring_engine"


def test_override_preserves_ai_score_and_recomputes_totals(
    criteria: AuditCriteria, tickets: list[IncidentTicket]
) -> None:
    excellent = next(ticket for ticket in tickets if ticket.ticket_id == "INC1001")
    engine = _engine(criteria, MockAuditModel())
    record = asyncio.run(engine.audit(excellent, job_id="job", version=1, audit_id="audit"))
    assert record.percentage == 100
    updated = engine.apply_override(
        record,
        measure_id="user_engagement",
        auditor_score=1,
        auditor_comments="The customer update does not describe the blocker.",
        override_reason="Communication to the caller is thinner than the AI score implies.",
    )
    engagement = next(measure for measure in updated.measures if measure.measure_id == "user_engagement")
    assert engagement.ai_score == 5
    assert engagement.auditor_score == 1
    assert engagement.final_score == 1
    assert engagement.overridden is True
    assert engagement.final_score_is_system_extension is True
    assert updated.auditor_override is True
    assert updated.percentage == 73.33
    assert updated.classification == "Fair"
    assert updated.totals_computed_by == "scoring_engine"
    assert record.measures[0].ai_score == 5
