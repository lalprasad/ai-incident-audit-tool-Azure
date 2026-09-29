from __future__ import annotations

import json
from datetime import datetime

from app.audit.evidence_analyzer import EvidenceAnalyzer
from app.audit.scoring_engine import ScoringEngine
from app.audit.timeline_analyzer import TimelineAnalyzer
from app.ai.protocols import AuditModel
from app.models.audit import AuditRecord, AuditorReview, MeasureResult
from app.models.criteria import AuditCriteria
from app.models.ticket import IncidentTicket
from app.utils.errors import InvalidModelOutput, ScoringError
from app.utils.time import utcnow

KEY_FIELDS = ("short_description", "description", "state", "priority")
REVIEW_ORDER = [
    "insufficient evidence",
    "unsupported evidence",
    "conflicting information",
    "unclear root cause",
    "missing resolution ownership",
    "low AI confidence",
    "incomplete extracted structure",
]


class AuditEngine:
    def __init__(
        self,
        *,
        model: AuditModel,
        scoring: ScoringEngine,
        evidence: EvidenceAnalyzer,
        criteria: AuditCriteria,
        timeline: TimelineAnalyzer,
        system_prompt: str,
        user_prompt: str,
        ai_model: str,
        model_version: str,
    ) -> None:
        self._model = model
        self._scoring = scoring
        self._evidence = evidence
        self._criteria = criteria
        self._timeline = timeline
        self._system_prompt = system_prompt
        self._user_prompt = user_prompt
        self._ai_model = ai_model
        self._model_version = model_version

    async def audit(
        self,
        ticket: IncidentTicket,
        *,
        job_id: str,
        version: int,
        audit_id: str,
        audited_at: datetime | None = None,
    ) -> AuditRecord:
        events = self._timeline.extract(ticket)
        ticket = ticket.model_copy(update={"timeline": events})
        evaluation = await self._model.evaluate(
            ticket,
            self._criteria,
            self._system_prompt,
            self._render_user_prompt(ticket),
        )
        self._require_measures(evaluation.measures)
        validated = self._evidence.validate(evaluation, ticket)
        try:
            computation = self._scoring.compute(
                {measure.measure_id: measure.score for measure in validated.measures}
            )
        except ScoringError as exc:
            raise InvalidModelOutput(str(exc)) from exc

        measures = [self._to_result(measure) for measure in validated.measures]
        reasons = self.review_reasons(ticket, measures, validated.flags)
        return AuditRecord(
            id=audit_id,
            ticket_id=ticket.ticket_id or "",
            audit_version=version,
            audited_at=audited_at or utcnow(),
            job_id=job_id,
            overall_score=computation.total_score,
            maximum_score=computation.maximum_score,
            percentage=computation.percentage,
            classification=computation.classification,
            totals_computed_by="scoring_engine",
            ai_model=self._ai_model,
            criteria_version=self._criteria.version,
            prompt_version=self._criteria.prompt_version,
            model_version=self._model_version,
            measures=measures,
            human_review_required=bool(reasons),
            review_reasons=reasons,
            overall_strengths=list(validated.overall_strengths),
            overall_gaps=list(validated.overall_gaps),
            recommended_actions=list(validated.recommended_actions),
            ticket=ticket,
        )

    def apply_override(
        self,
        audit: AuditRecord,
        *,
        measure_id: str,
        auditor_score: int,
        auditor_comments: str | None,
        override_reason: str,
        reviewed_at: datetime | None = None,
    ) -> AuditRecord:
        self._scoring.validate_measure_score(measure_id, auditor_score)
        if measure_id not in {measure.measure_id for measure in audit.measures}:
            raise ScoringError(f"Unknown measure {measure_id}")
        updated: list[MeasureResult] = []
        for measure in audit.measures:
            if measure.measure_id != measure_id:
                updated.append(measure)
                continue
            level = self._criteria.level(measure_id, auditor_score)
            updated.append(
                measure.model_copy(
                    update={
                        "auditor_score": auditor_score,
                        "final_score": auditor_score,
                        "auditor_comments": auditor_comments,
                        "override_reason": override_reason,
                        "overridden": True,
                        "final_score_is_system_extension": level.system_defined_extension,
                        "guidance": level.guidance,
                    }
                )
            )
        computation = self._scoring.compute({item.measure_id: item.final_score for item in updated})
        return audit.model_copy(
            update={
                "measures": updated,
                "overall_score": computation.total_score,
                "maximum_score": computation.maximum_score,
                "percentage": computation.percentage,
                "classification": computation.classification,
                "auditor_override": True,
                "totals_computed_by": "scoring_engine",
                "auditor_review": AuditorReview(
                    decision="override",
                    comments=auditor_comments,
                    reviewed_at=reviewed_at or utcnow(),
                ),
            }
        )

    def accept(self, audit: AuditRecord, comments: str | None, *, decision: str) -> AuditRecord:
        return audit.model_copy(
            update={
                "auditor_review": AuditorReview(
                    decision=decision,
                    comments=comments,
                    reviewed_at=utcnow(),
                )
            }
        )

    def review_reasons(
        self,
        ticket: IncidentTicket,
        measures: list[MeasureResult],
        model_flags: list[str],
    ) -> list[str]:
        reasons: list[str] = []

        def add(reason: str) -> None:
            if reason not in reasons:
                reasons.append(reason)

        for flag in model_flags:
            if flag in REVIEW_ORDER:
                add(flag)
        for measure in measures:
            supported = [item for item in measure.evidence if item.evidence_status == "Supported"]
            if not supported:
                add("insufficient evidence")
            if measure.measure_id == "issue_diagnosis" and measure.final_score <= 2:
                add("unclear root cause")
            if any("not explicitly documented" in gap for gap in measure.gaps) and measure.measure_id == "solutioning":
                add("missing resolution ownership")
            if self._criteria.confidence_label(measure.confidence) == "Requires human review":
                add("low AI confidence")
        filled = sum(1 for name in KEY_FIELDS if getattr(ticket, name))
        if filled < 3:
            add("incomplete extracted structure")
        return [reason for reason in REVIEW_ORDER if reason in reasons]

    def _to_result(self, measure) -> MeasureResult:
        level = self._criteria.level(measure.measure_id, measure.score)
        return MeasureResult(
            measure_id=measure.measure_id,
            measure_name=measure.measure_name,
            ai_score=measure.score,
            final_score=measure.score,
            confidence=measure.confidence,
            confidence_label=self._criteria.confidence_label(measure.confidence),
            evidence=list(measure.evidence),
            strengths=list(measure.strengths),
            gaps=list(measure.gaps),
            recommendation=measure.recommendation,
            ai_score_is_system_extension=level.system_defined_extension,
            final_score_is_system_extension=level.system_defined_extension,
            guidance=level.guidance,
        )

    def _require_measures(self, measures) -> None:
        expected = set(self._criteria.measure_ids())
        found = [measure.measure_id for measure in measures]
        if len(found) != len(set(found)) or set(found) != expected:
            raise InvalidModelOutput("Model did not return each audit measure once")

    def _render_user_prompt(self, ticket: IncidentTicket) -> str:
        criteria_json = self._criteria.model_dump_json()
        incident_json = json.dumps(ticket.llm_payload(), ensure_ascii=True)
        return (
            self._user_prompt.replace("{{incident_json}}", incident_json).replace(
                "{{criteria_json}}", criteria_json
            )
        )
