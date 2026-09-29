from __future__ import annotations

import re

from app.audit.timeline_analyzer import parse_timestamp
from app.models.ticket import IncidentTicket, RawSegment

TICKET_ID_PATTERN = re.compile(r"\b(INC\d+)\b", re.IGNORECASE)


class TicketNormalizer:
    """Map extracted fields onto the incident model. Missing fields stay empty."""

    def normalize(self, segment: RawSegment) -> IncidentTicket:
        fields = segment.fields
        ticket_id = self._ticket_id(fields.get("ticket_id", ""))
        return IncidentTicket(
            ticket_id=ticket_id,
            short_description=self._text(fields.get("short_description")),
            description=self._text(fields.get("description")),
            priority=self._text(fields.get("priority")),
            severity=self._text(fields.get("severity")),
            assignment_group=self._text(fields.get("assignment_group")),
            assigned_to=self._text(fields.get("assigned_to")),
            caller=self._text(fields.get("caller")),
            business_service=self._text(fields.get("business_service")),
            configuration_item=self._text(fields.get("configuration_item")),
            opened_at=parse_timestamp(fields["opened_at"]) if fields.get("opened_at") else None,
            updated_at=parse_timestamp(fields["updated_at"]) if fields.get("updated_at") else None,
            resolved_at=parse_timestamp(fields["resolved_at"]) if fields.get("resolved_at") else None,
            closed_at=parse_timestamp(fields["closed_at"]) if fields.get("closed_at") else None,
            state=self._text(fields.get("state")),
            work_notes=self._text(fields.get("work_notes")),
            additional_comments=self._text(fields.get("additional_comments")),
            resolution_notes=self._text(fields.get("resolution_notes")),
            resolution_code=self._text(fields.get("resolution_code")),
            cause=self._text(fields.get("cause")),
            close_notes=self._text(fields.get("close_notes")),
            raw_text=segment.raw_text,
            source_pages=list(segment.source_pages),
        )

    def _text(self, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    def _ticket_id(self, value: str) -> str | None:
        match = TICKET_ID_PATTERN.search(value or "")
        if not match:
            return None
        return match.group(1).upper()
