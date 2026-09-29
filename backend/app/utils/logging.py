from __future__ import annotations

import json
import logging

FORBIDDEN_LOG_FIELDS = {
    "raw_text",
    "content",
    "work_notes",
    "description",
    "additional_comments",
    "resolution_notes",
    "cause",
    "prompt",
    "incident_json",
}


class AuditLogger:
    """Structured logs. Ticket bodies are dropped even if a caller passes them."""

    def __init__(self, name: str = "incident_audit") -> None:
        self._logger = logging.getLogger(name)

    def event(self, *, stage: str, status: str, **fields: object) -> None:
        payload: dict[str, object] = {"stage": stage, "status": status}
        for key, value in fields.items():
            if key in FORBIDDEN_LOG_FIELDS or value is None:
                continue
            payload[key] = value
        self._logger.info(json.dumps(payload, default=str))
