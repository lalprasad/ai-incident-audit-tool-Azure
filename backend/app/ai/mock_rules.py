from __future__ import annotations

import re
from datetime import datetime

from app.models.criteria import AuditCriteria
from app.models.llm import EvidenceItem, LlmAuditEvaluation, MeasureEvaluation
from app.models.ticket import IncidentTicket, TimelineEvent

ENGAGEMENT_SIGNALS: dict[str, re.Pattern[str]] = {
    "acknowledgement": re.compile(r"\backnowledg|\btriaged\b", re.IGNORECASE),
    "investigation": re.compile(r"\binvestigat", re.IGNORECASE),
    "progress": re.compile(r"\bprogress\b|\bidentified\b|\bconfirmed\b", re.IGNORECASE),
    "blocker": re.compile(r"\bblocker\b|\bblocked\b|\bwaiting on\b", re.IGNORECASE),
    "next_steps": re.compile(r"\bnext step|\bwill update\b", re.IGNORECASE),
    "resolution_communication": re.compile(
        r"\bresolved\b|\brestored\b|\bresolution communicated\b", re.IGNORECASE
    ),
}
ACTION_PATTERN = re.compile(
    r"\brestart|\bapplied\b|\brolled back\b|\bpatched\b|\bcleared\b|\bfailed over\b|\bupdated the\b",
    re.IGNORECASE,
)
WHO_PATTERN = re.compile(
    r"\bperformed by\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+"
    r"|\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+(?:restarted|applied|rolled|patched|cleared|failed over|updated|executed)\b"
)
VALIDATION_PATTERN = re.compile(
    r"\bvalidat|\bconfirmed recovery\b|\breturned to baseline\b|\bprobes passed\b",
    re.IGNORECASE,
)
ROOT_CAUSE_LINE = re.compile(r"root cause:\s*(.+)", re.IGNORECASE)
MEANINGFUL_CHARS = 30

CONFIDENCE_BY_SCORE = {5: 0.93, 4: 0.88, 3: 0.76, 2: 0.66, 1: 0.52}


def _notes(ticket: IncidentTicket) -> str:
    return "\n".join(part for part in (ticket.work_notes, ticket.additional_comments) if part)


def _diagnosis_text(ticket: IncidentTicket) -> str:
    # Resolution text can name a component that was changed. That is not a diagnosis.
    return "\n".join(part for part in (ticket.cause, ticket.description, ticket.close_notes) if part)


def _solution_text(ticket: IncidentTicket) -> str:
    return "\n".join(part for part in (ticket.resolution_notes, ticket.close_notes) if part)


def _page(ticket: IncidentTicket) -> int | None:
    return ticket.source_pages[0] if ticket.source_pages else None


def _quote_line(text: str, pattern: re.Pattern[str]) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if pattern.search(stripped) and len(stripped) >= 12:
            return stripped
    return None


def _timestamp_for(quote: str, events: list[TimelineEvent]) -> str | None:
    for event in events:
        if event.timestamp and quote and quote in event.text:
            return event.timestamp.strftime("%Y-%m-%d %H:%M")
    return None


def _supported(
    text: str,
    field: str,
    relevance: str,
    ticket: IncidentTicket,
    events: list[TimelineEvent],
) -> EvidenceItem:
    return EvidenceItem(
        text=text,
        source_section=field,
        ticket_field=field,
        relevance=relevance,
        evidence_status="Supported",
        timestamp=_timestamp_for(text, events),
        page=_page(ticket),
    )


def _insufficient(message: str, field: str, ticket: IncidentTicket) -> EvidenceItem:
    return EvidenceItem(
        text=message,
        source_section=field,
        ticket_field=field,
        relevance="The ticket does not contain enough information to support a higher score.",
        evidence_status="Insufficient evidence",
        page=_page(ticket),
    )


def _priority_key(priority: str | None) -> str:
    if not priority:
        return "4"
    match = re.search(r"[1-4]", priority)
    return match.group(0) if match else "4"


def _hours(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 3600


def engagement_score(ticket: IncidentTicket, criteria: AuditCriteria) -> tuple[int, dict[str, bool], int]:
    notes = _notes(ticket)
    signals = {name: bool(pattern.search(notes)) for name, pattern in ENGAGEMENT_SIGNALS.items()}
    meaningful = sum(1 for event in ticket.timeline if len(event.text.strip()) >= MEANINGFUL_CHARS)
    present = sum(1 for found in signals.values() if found)
    if present >= 6 and meaningful >= 4:
        score = 5
    elif present >= 4 and meaningful >= 3:
        score = 4
    elif present >= 2 and meaningful >= 2:
        score = 3
    elif present >= 1 or meaningful >= 1:
        score = 2
    else:
        score = 1
    score = _apply_timeliness(score, ticket, criteria)
    return score, signals, meaningful


def _apply_timeliness(score: int, ticket: IncidentTicket, criteria: AuditCriteria) -> int:
    guidance = criteria.timeliness
    if not guidance.penalize_when_first_update_and_longest_gap_exceed or score <= 1:
        return score
    stamped = [event for event in ticket.timeline if event.timestamp is not None]
    if ticket.opened_at is None or len(stamped) < 2:
        return score
    expectation = guidance.priority_first_update_hours.get(_priority_key(ticket.priority), 24)
    times = sorted(event.timestamp for event in stamped if event.timestamp is not None)
    delay = _hours(ticket.opened_at, times[0])
    longest_gap = max(_hours(earlier, later) for earlier, later in zip(times, times[1:]))
    if delay > expectation and longest_gap > expectation:
        return max(1, score - 1)
    return score


def _conflicting_causes(text: str) -> bool:
    chunks = re.findall(
        r"root cause:\s*(.+?)(?=root cause:|$)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    found = [re.sub(r"\s+", " ", item).strip(" .").lower() for item in chunks if item.strip()]
    if len(found) < 2:
        return False
    first, second = found[0], found[1]
    return first not in second and second not in first


def diagnosis_score(ticket: IncidentTicket) -> tuple[int, bool]:
    text = _diagnosis_text(ticket)
    if _conflicting_causes(text):
        return 2, True
    has_root = bool(re.search(r"\broot cause\b", text, re.IGNORECASE))
    has_what = has_root or bool(re.search(r"\bcaused by\b", text, re.IGNORECASE))
    has_where = bool(re.search(r"\boccurred in\b|\baffected component\b", text, re.IGNORECASE))
    if ticket.configuration_item and ticket.configuration_item.lower() in text.lower():
        has_where = True
    has_why = bool(re.search(r"\bbecause\b|\bdue to\b", text, re.IGNORECASE))
    if has_what and has_where and has_why:
        return 5, False
    if has_what and (has_where or has_why):
        return 4, False
    if (has_where or has_why) and not has_what:
        return 3, False
    if has_what:
        return 3, False
    return 1, False


def solution_score(ticket: IncidentTicket) -> tuple[int, bool, bool, bool]:
    text = _solution_text(ticket)
    resolution = ticket.resolution_notes or ""
    action = bool(ACTION_PATTERN.search(text))
    who = bool(WHO_PATTERN.search(resolution))
    validation = bool(VALIDATION_PATTERN.search(text))
    if not text.strip():
        return 1, action, who, validation
    if action and who and validation:
        return 5, action, who, validation
    if action and who:
        return 4, action, who, validation
    if action and validation and not who:
        return 2, action, who, validation
    if action:
        return 3, action, who, validation
    if len(text) > 20:
        return 2, action, who, validation
    return 1, action, who, validation


def _confidence(score: int, *, conflict: bool) -> float:
    value = CONFIDENCE_BY_SCORE[score]
    if conflict:
        value = min(value, 0.61)
    return value


def evaluate_ticket(ticket: IncidentTicket, criteria: AuditCriteria) -> LlmAuditEvaluation:
    """Deterministic stand-in for Azure OpenAI. Quotes are slices of the ticket."""

    engagement, signals, _meaningful = engagement_score(ticket, criteria)
    diagnosis, conflict = diagnosis_score(ticket)
    solution, action, who, validation = solution_score(ticket)
    messages = criteria.messages
    events = ticket.timeline

    engagement_measure = _engagement_measure(ticket, criteria, engagement, signals, events)
    diagnosis_measure = _diagnosis_measure(ticket, criteria, diagnosis, conflict, events)
    solution_measure = _solution_measure(
        ticket, criteria, solution, action, who, validation, events
    )
    measures = [engagement_measure, diagnosis_measure, solution_measure]

    flags: list[str] = []
    if conflict:
        flags.append("conflicting information")
    if diagnosis <= 2:
        flags.append("unclear root cause")
    if action and not who and _solution_text(ticket).strip():
        flags.append("missing resolution ownership")
    if any(item.evidence_status == "Insufficient evidence" and not any(
        evidence.evidence_status == "Supported" for evidence in measure.evidence
    ) for measure in measures for item in measure.evidence):
        flags.append("insufficient evidence")
    if any(_confidence_requires_review(measure.confidence, criteria) for measure in measures):
        flags.append("low AI confidence")

    gaps = [gap for measure in measures for gap in measure.gaps]
    strengths = [item for measure in measures for item in measure.strengths]
    actions = []
    for measure in measures:
        if measure.score < 5 and measure.recommendation not in actions:
            actions.append(measure.recommendation)

    return LlmAuditEvaluation(
        ticket_id=ticket.ticket_id,
        measures=measures,
        overall_strengths=strengths[:6],
        overall_gaps=gaps,
        recommended_actions=actions,
        flags=flags,
        overall_score=None,
        percentage=None,
        classification=None,
    )


def _confidence_requires_review(confidence: float, criteria: AuditCriteria) -> bool:
    return criteria.confidence_label(confidence) == "Requires human review"


def _engagement_measure(
    ticket: IncidentTicket,
    criteria: AuditCriteria,
    score: int,
    signals: dict[str, bool],
    events: list[TimelineEvent],
) -> MeasureEvaluation:
    messages = criteria.messages
    evidence: list[EvidenceItem] = []
    notes = _notes(ticket)
    seen: set[str] = set()
    for name, pattern in ENGAGEMENT_SIGNALS.items():
        if not signals[name]:
            continue
        quote = _quote_line(notes, pattern)
        if not quote or quote in seen:
            continue
        seen.add(quote)
        field = "work_notes" if quote in (ticket.work_notes or "") else "additional_comments"
        evidence.append(
            _supported(
                quote,
                field,
                f"Documented {name.replace('_', ' ')} during the investigation.",
                ticket,
                events,
            )
        )
    gaps: list[str] = []
    strengths: list[str] = []
    if score <= 2:
        gaps.append(messages.updates_missing)
    elif score == 3:
        gaps.append(
            "Updates are infrequent or thin. Progress, blockers, and next steps are not consistently visible."
        )
    elif score == 4:
        gaps.append("Investigation communication is regular, with a minor gap in the update trail.")
    if score >= 4 and any(signals.values()):
        strengths.append("The ticket contains a sequence of investigation updates.")
    if not evidence:
        evidence.append(_insufficient(messages.updates_missing, "work_notes", ticket))
    recommendation = {
        5: "Keep recording acknowledgement, progress, blockers, next steps, and resolution when they happen.",
        4: "Close the remaining communication gap so blockers and next steps are explicit when they exist.",
        3: "Add timed updates that describe progress, blockers, and the next step, scaled to the priority.",
        2: "Add investigation updates. A thin trail does not show how the incident was handled.",
        1: "Add investigation updates. Absence of notes is not evidence that communication happened.",
    }[score]
    return _measure("user_engagement", criteria, score, evidence, strengths, gaps, recommendation, False)


def _diagnosis_measure(
    ticket: IncidentTicket,
    criteria: AuditCriteria,
    score: int,
    conflict: bool,
    events: list[TimelineEvent],
) -> MeasureEvaluation:
    messages = criteria.messages
    text = _diagnosis_text(ticket)
    evidence: list[EvidenceItem] = []
    gaps: list[str] = []
    strengths: list[str] = []
    if conflict:
        for line in text.splitlines():
            if ROOT_CAUSE_LINE.search(line):
                evidence.append(
                    _supported(
                        line.strip(),
                        "cause",
                        "One of the conflicting root-cause statements.",
                        ticket,
                        events,
                    )
                )
        gaps.append(messages.conflict)
    elif score >= 4:
        quote = _quote_line(text, re.compile(r"root cause:|caused by", re.IGNORECASE))
        if quote:
            evidence.append(
                _supported(quote, "cause", "States a cause in the ticket text.", ticket, events)
            )
        if score == 5:
            strengths.append("The ticket states what failed, where it occurred, and why.")
        else:
            strengths.append("The ticket documents a cause and at least one of location or reason.")
            gaps.append("One diagnostic question is still thin or missing.")
    elif score == 3:
        quote = _quote_line(text, re.compile(r"occurred in|due to|because", re.IGNORECASE))
        if quote:
            evidence.append(
                _supported(
                    quote,
                    "description",
                    "Partial diagnosis. This does not identify a root cause on its own.",
                    ticket,
                    events,
                )
            )
        gaps.append("Partial diagnosis with limited root cause detail.")
    else:
        symptom = _quote_line(text, re.compile(r".+", re.IGNORECASE))
        if symptom:
            evidence.append(
                _supported(
                    symptom,
                    "description",
                    messages.symptom_not_cause,
                    ticket,
                    events,
                )
            )
        gaps.append(messages.root_cause_missing)
        if not evidence:
            evidence.append(_insufficient(messages.root_cause_missing, "cause", ticket))
    recommendation = {
        5: "Keep recording the root cause, the component, and why it happened in the cause field.",
        4: "Add the missing diagnostic dimension so what, where, and why are all explicit.",
        3: "Document the root cause. Location or a reason alone is only a partial diagnosis.",
        2: "Resolve the conflicting statements and record one supported root cause.",
        1: "Document what caused the issue, where it occurred, and why. Do not stop at the symptom.",
    }[score if not conflict else 2]
    if conflict:
        recommendation = "Resolve the conflicting statements and record one supported root cause."
    return _measure(
        "issue_diagnosis", criteria, score, evidence, strengths, gaps, recommendation, conflict
    )


def _solution_measure(
    ticket: IncidentTicket,
    criteria: AuditCriteria,
    score: int,
    action: bool,
    who: bool,
    validation: bool,
    events: list[TimelineEvent],
) -> MeasureEvaluation:
    messages = criteria.messages
    text = _solution_text(ticket)
    evidence: list[EvidenceItem] = []
    gaps: list[str] = []
    strengths: list[str] = []
    quote = None
    if ticket.resolution_notes:
        quote = ticket.resolution_notes.strip().splitlines()[0].strip()
    elif ticket.close_notes:
        quote = ticket.close_notes.strip().splitlines()[0].strip()
    if quote and len(quote) >= 12 and score > 1:
        evidence.append(
            _supported(quote, "resolution_notes", "Resolution text from the ticket.", ticket, events)
        )
    if who and action:
        strengths.append("The resolution names the person who performed the action.")
    if validation:
        strengths.append("Recovery validation is documented.")
    if not text.strip():
        gaps.append(messages.resolution_missing)
        evidence.append(_insufficient(messages.resolution_missing, "resolution_notes", ticket))
    elif action and not who:
        gaps.append(messages.ownership_missing)
        if not validation:
            gaps.append("Validation of the fix is not documented.")
    elif action and who and not validation:
        gaps.append("Validation of the fix is not fully documented.")
    elif not action:
        gaps.append("The resolution text does not describe the action that was taken.")
    recommendation = {
        5: "Keep the action, the named owner, and the validation result together in the resolution notes.",
        4: "Add how recovery was validated, in the words of the check that was performed.",
        3: "Name who performed the fix and record the check that showed recovery.",
        2: "Name who performed the fix. Do not leave ownership implied by the assignment field.",
        1: "Document what was done, who did it, and how recovery was confirmed.",
    }[score]
    return _measure("solutioning", criteria, score, evidence, strengths, gaps, recommendation, False)


def _measure(
    measure_id: str,
    criteria: AuditCriteria,
    score: int,
    evidence: list[EvidenceItem],
    strengths: list[str],
    gaps: list[str],
    recommendation: str,
    conflict: bool,
) -> MeasureEvaluation:
    definition = criteria.measure(measure_id)
    return MeasureEvaluation(
        measure_id=measure_id,
        measure_name=definition.name,
        score=score,
        confidence=_confidence(score, conflict=conflict),
        evidence=evidence,
        strengths=strengths,
        gaps=gaps,
        recommendation=recommendation,
    )
