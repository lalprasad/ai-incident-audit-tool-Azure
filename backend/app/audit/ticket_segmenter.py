from __future__ import annotations

import re

from app.models.ticket import PageText, RawSegment

BOUNDARY = re.compile(r"(?=^(?:INCIDENT NUMBER|Number)\s*:)", re.IGNORECASE | re.MULTILINE)
HEADER = re.compile(r"^([A-Za-z][A-Za-z /]+):\s*(.*)$")

SECTION_FIELDS = {
    "DESCRIPTION": "description",
    "CAUSE": "cause",
    "RESOLUTION NOTES": "resolution_notes",
    "CLOSE NOTES": "close_notes",
    "WORK NOTES": "work_notes",
    "ADDITIONAL COMMENTS": "additional_comments",
}

SINGLE_FIELDS = {
    "INCIDENT NUMBER": "ticket_id",
    "NUMBER": "ticket_id",
    "SHORT DESCRIPTION": "short_description",
    "PRIORITY": "priority",
    "SEVERITY": "severity",
    "STATE": "state",
    "ASSIGNMENT GROUP": "assignment_group",
    "ASSIGNED TO": "assigned_to",
    "CALLER": "caller",
    "BUSINESS SERVICE": "business_service",
    "CONFIGURATION ITEM": "configuration_item",
    "OPENED AT": "opened_at",
    "UPDATED AT": "updated_at",
    "RESOLVED AT": "resolved_at",
    "CLOSED AT": "closed_at",
    "RESOLUTION CODE": "resolution_code",
}


class TicketSegmenter:
    def segment(self, pages: list[PageText]) -> list[RawSegment]:
        full, spans = self._join_pages(pages)
        matches = list(BOUNDARY.finditer(full))
        segments: list[RawSegment] = []
        for index, match in enumerate(matches):
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(full)
            raw = full[start:end].strip()
            if not raw:
                continue
            pages_hit = [number for span_start, span_end, number in spans if span_start < end and span_end > start]
            segments.append(
                RawSegment(
                    raw_text=raw,
                    source_pages=pages_hit,
                    fields=self.parse_fields(raw),
                )
            )
        return segments

    def parse_fields(self, raw: str) -> dict[str, str]:
        current: str | None = None
        buffer: list[str] = []
        data: dict[str, list[str]] = {}

        def flush() -> None:
            if current is None:
                return
            text = "\n".join(buffer).strip()
            if text:
                data.setdefault(current, []).append(text)

        for line in raw.splitlines():
            header = HEADER.match(line.strip())
            label = re.sub(r"\s+", " ", header.group(1).strip().upper()) if header else ""
            if header and (label in SECTION_FIELDS or label in SINGLE_FIELDS):
                rest = header.group(2).strip()
                if label in SECTION_FIELDS:
                    flush()
                    current = SECTION_FIELDS[label]
                    buffer = [rest] if rest else []
                    continue
                if label in SINGLE_FIELDS:
                    flush()
                    current = None
                    buffer = []
                    field = SINGLE_FIELDS[label]
                    if rest:
                        data.setdefault(field, []).append(rest)
                    continue
            if current is not None:
                buffer.append(line.strip())
        flush()
        return {key: "\n".join(parts).strip() for key, parts in data.items() if "\n".join(parts).strip()}

    def _join_pages(self, pages: list[PageText]) -> tuple[str, list[tuple[int, int, int]]]:
        parts: list[str] = []
        spans: list[tuple[int, int, int]] = []
        cursor = 0
        for index, page in enumerate(pages):
            if index:
                parts.append("\n")
                cursor += 1
            text = page.text.replace("\r\n", "\n").replace("\r", "\n")
            start = cursor
            parts.append(text)
            cursor += len(text)
            spans.append((start, cursor, page.number))
        return "".join(parts), spans
