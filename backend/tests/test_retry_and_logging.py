import asyncio
import json
import logging

import pytest

from app.utils.errors import InvalidModelOutput, TransientError
from app.utils.logging import AuditLogger
from app.utils.retry import with_retries


def test_retries_transient_failures_and_stops_on_permanent_errors() -> None:
    calls = {"count": 0}

    async def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise TransientError("timeout")
        return "ok"

    assert asyncio.run(with_retries(flaky, retries=3, base_delay=0)) == "ok"
    assert calls["count"] == 3

    async def invalid():
        raise InvalidModelOutput("bad json")

    with pytest.raises(InvalidModelOutput):
        asyncio.run(with_retries(invalid, retries=4, base_delay=0))


def test_logs_drop_ticket_content(caplog: pytest.LogCaptureFixture) -> None:
    logger = AuditLogger()
    with caplog.at_level(logging.INFO, logger="incident_audit"):
        logger.event(
            stage="score",
            status="Completed",
            job_id="job-1",
            ticket_id="INC1001",
            work_notes="secret investigation detail",
            description="secret description",
            raw_text="full ticket",
            llm_latency_ms=12,
            retry_count=1,
        )
    assert len(caplog.records) == 1
    payload = json.loads(caplog.records[0].message)
    assert payload["ticket_id"] == "INC1001"
    assert payload["llm_latency_ms"] == 12
    assert "work_notes" not in payload
    assert "secret" not in caplog.records[0].message
