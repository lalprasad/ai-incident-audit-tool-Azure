from __future__ import annotations

import csv
import io
from datetime import datetime

from openpyxl import Workbook

from app.models.audit import AuditRecord, MeasureResult
from app.models.dashboard import DashboardSummary

EXPORT_COLUMNS = [
    "Ticket ID",
    "Audit Version",
    "Audited At",
    "Short Description",
    "Priority",
    "Severity",
    "State",
    "Assignment Group",
    "Assigned To",
    "Opened At",
    "Resolved At",
    "User Engagement AI Score",
    "User Engagement Final Score",
    "Issue Diagnosis AI Score",
    "Issue Diagnosis Final Score",
    "Solutioning AI Score",
    "Solutioning Final Score",
    "Overall Score",
    "Maximum Score",
    "Percentage",
    "Classification",
    "Human Review Required",
    "Review Reasons",
    "Auditor Override",
    "Top Gaps",
    "Recommended Actions",
    "Criteria Version",
    "Prompt Version",
    "Model Version",
    "Totals Computed By",
]

_MEASURES = (
    ("user_engagement", "User Engagement"),
    ("issue_diagnosis", "Issue Diagnosis"),
    ("solutioning", "Solutioning"),
)


def render_csv(audits: list[AuditRecord]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_COLUMNS)
    writer.writeheader()
    for audit in audits:
        writer.writerow({key: _safe(value) for key, value in _row(audit).items()})
    return buffer.getvalue().encode("utf-8-sig")


def render_xlsx(audits: list[AuditRecord], summary: DashboardSummary) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Audits"
    sheet.append(EXPORT_COLUMNS)
    for audit in audits:
        row = _row(audit)
        sheet.append([row[column] for column in EXPORT_COLUMNS])
    overview = workbook.create_sheet("Summary")
    overview.append(["Executive summary"])
    overview.append([summary.executive_summary])
    overview.append([])
    overview.append(["Total tickets", summary.total_tickets])
    overview.append(["Average percentage", summary.average_percentage])
    overview.append(["Human review", summary.human_review_count])
    payload = io.BytesIO()
    workbook.save(payload)
    return payload.getvalue()


def _row(audit: AuditRecord) -> dict[str, object]:
    ticket = audit.ticket
    by_id = {measure.measure_id: measure for measure in audit.measures}
    row: dict[str, object] = {
        "Ticket ID": audit.ticket_id,
        "Audit Version": audit.audit_version,
        "Audited At": _stamp(audit.audited_at),
        "Short Description": ticket.short_description or "",
        "Priority": ticket.priority or "",
        "Severity": ticket.severity or "",
        "State": ticket.state or "",
        "Assignment Group": ticket.assignment_group or "",
        "Assigned To": ticket.assigned_to or "",
        "Opened At": _stamp(ticket.opened_at),
        "Resolved At": _stamp(ticket.resolved_at),
        "Overall Score": audit.overall_score,
        "Maximum Score": audit.maximum_score,
        "Percentage": audit.percentage,
        "Classification": audit.classification,
        "Human Review Required": "Yes" if audit.human_review_required else "No",
        "Review Reasons": " | ".join(audit.review_reasons),
        "Auditor Override": "Yes" if audit.auditor_override else "No",
        "Top Gaps": " | ".join(audit.overall_gaps),
        "Recommended Actions": " | ".join(audit.recommended_actions),
        "Criteria Version": audit.criteria_version,
        "Prompt Version": audit.prompt_version,
        "Model Version": audit.model_version,
        "Totals Computed By": audit.totals_computed_by,
    }
    for measure_id, label in _MEASURES:
        measure = by_id.get(measure_id)
        row[f"{label} AI Score"] = _score(measure, "ai")
        row[f"{label} Final Score"] = _score(measure, "final")
    return row


def _score(measure: MeasureResult | None, kind: str) -> int | str:
    if measure is None:
        return ""
    return measure.ai_score if kind == "ai" else measure.final_score


def _stamp(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat(sep=" ", timespec="minutes")


def _safe(value: object) -> str:
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text
