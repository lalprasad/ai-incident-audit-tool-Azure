from __future__ import annotations

import re
from datetime import datetime

from app.models.ticket import IncidentTicket, TimelineEvent

NOTE_PATTERN = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\]\s+(?P<author>.+?)\s+\((?P<audience>internal|customer)\):\s*(?P<text>.+)$",
    re.IGNORECASE,
)
TIMESTAMP_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S")


def parse_timestamp(value: str) -> datetime | None:
    text = value.strip()
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def classify_event(text: str) -> str:
    lowered = text.lower()
    if re.search(r"\bassigned\b", lowered):
        return "assignment"
    if re.search(r"\backnowledg|\btriaged\b", lowered):
        return "acknowledgement"
    if re.search(r"\bblocker\b|\bblocked\b|\bwaiting on\b", lowered):
        return "blocker"
    if re.search(r"\bstate changed\b|\bmoved to\b", lowered):
        return "state_change"
    if re.search(r"\bresolved\b|\brestored\b|\bresolution communicated\b", lowered):
        return "resolution"
    if re.search(r"\binvestigat|\bidentified\b|\bprogress\b|\bnext step\b", lowered):
        return "investigation"
    return "comment"


class TimelineAnalyzer:
    def extract(self, ticket: IncidentTicket) -> list[TimelineEvent]:
        events: list[TimelineEvent] = []
        events.extend(self._parse_block(ticket.work_notes))
        events.extend(self._parse_block(ticket.additional_comments))
        events.sort(key=lambda event: (event.timestamp is None, event.timestamp or datetime.min))
        return events

    def _parse_block(self, block: str | None) -> list[TimelineEvent]:
        if not block:
            return []
        events: list[TimelineEvent] = []
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            match = NOTE_PATTERN.match(stripped)
            if not match:
                events.append(
                    TimelineEvent(
                        event_type=classify_event(stripped),
                        text=stripped,
                        audience="unknown",
                    )
                )
                continue
            audience = match.group("audience").lower()
            if audience not in {"internal", "customer"}:
                audience = "unknown"
            text = match.group("text").strip()
            events.append(
                TimelineEvent(
                    timestamp=parse_timestamp(match.group("timestamp")),
                    author=match.group("author").strip(),
                    event_type=classify_event(text),
                    text=text,
                    audience=audience,  # type: ignore[arg-type]
                )
            )
        return events
