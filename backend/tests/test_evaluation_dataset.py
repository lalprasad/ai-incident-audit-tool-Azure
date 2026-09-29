import asyncio
import json
from pathlib import Path

from app.audit.audit_engine import AuditEngine
from app.audit.evidence_analyzer import EvidenceAnalyzer, quote_supported, ticket_corpus
from app.audit.scoring_engine import ScoringEngine
from app.audit.timeline_analyzer import TimelineAnalyzer
from app.ai.mock_openai import MockAuditModel
from app.models.audit import AuditRecord
from app.models.criteria import AuditCriteria
from app.models.ticket import IncidentTicket

ROOT = Path(__file__).resolve().parents[2]


def _audit(criteria: AuditCriteria, ticket: IncidentTicket) -> AuditRecord:
    scoring = ScoringEngine(criteria)
    engine = AuditEngine(
        model=MockAuditModel(),
        scoring=scoring,
        evidence=EvidenceAnalyzer(scoring),
        criteria=criteria,
        timeline=TimelineAnalyzer(),
        system_prompt="auditor",
        user_prompt="{{incident_json}} {{criteria_json}}",
        ai_model="mock-deterministic",
        model_version="mock-rules-1.0.0",
    )
    return asyncio.run(engine.audit(ticket, job_id="job", version=1, audit_id=ticket.ticket_id or "audit"))


def test_sample_tickets_fall_in_expected_ranges(
    criteria: AuditCriteria, tickets: list[IncidentTicket]
) -> None:
    dataset = json.loads((ROOT / "sample-data" / "evaluation-dataset.json").read_text(encoding="utf-8"))
    by_id = {ticket.ticket_id: ticket for ticket in tickets}
    for expected in dataset["tickets"]:
        record = _audit(criteria, by_id[expected["ticket_id"]])
        if "percentage_min" in expected:
            assert expected["percentage_min"] <= record.percentage <= expected["percentage_max"]
        if "classification" in expected:
            assert record.classification == expected["classification"]
        assert record.human_review_required is expected["expect_human_review"]
        assert record.totals_computed_by == "scoring_engine"
        corpus = ticket_corpus(record.ticket)
        for measure in record.measures:
            for item in measure.evidence:
                if item.evidence_status == "Supported":
                    assert quote_supported(item.text, corpus)
        if "diagnosis_max" in expected:
            diagnosis = next(item for item in record.measures if item.measure_id == "issue_diagnosis")
            assert diagnosis.final_score <= expected["diagnosis_max"]
        if "solutioning_max" in expected:
            solution = next(item for item in record.measures if item.measure_id == "solutioning")
            assert solution.final_score <= expected["solutioning_max"]
        if "engagement_max" in expected:
            engagement = next(item for item in record.measures if item.measure_id == "user_engagement")
            assert engagement.final_score <= expected["engagement_max"]
        if "required_gap" in expected:
            assert expected["required_gap"] in record.overall_gaps
        if "required_flag" in expected:
            assert expected["required_flag"] in record.review_reasons
