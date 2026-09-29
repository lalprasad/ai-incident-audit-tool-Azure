from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.audit.ticket_normalizer import TicketNormalizer
from app.audit.ticket_segmenter import TicketSegmenter
from app.audit.timeline_analyzer import TimelineAnalyzer
from app.config.criteria_loader import load_criteria
from app.config.settings import Settings
from app.main import create_app
from app.models.criteria import AuditCriteria
from app.models.ticket import IncidentTicket, PageText

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_TEXT = REPO_ROOT / "sample-data" / "multi-ticket.txt"
CRITERIA_PATH = REPO_ROOT / "backend" / "app" / "config" / "audit_criteria.json"


@pytest.fixture(scope="session", autouse=True)
def built_sample_pdf() -> Path:
    import importlib.util

    script = REPO_ROOT / "sample-data" / "build_pdf.py"
    spec = importlib.util.spec_from_file_location("build_sample_pdf", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build()


@pytest.fixture
def criteria() -> AuditCriteria:
    return load_criteria(CRITERIA_PATH)


@pytest.fixture
def sample_text() -> str:
    return SAMPLE_TEXT.read_text(encoding="utf-8")


def load_tickets(text: str) -> list[IncidentTicket]:
    segmenter = TicketSegmenter()
    normalizer = TicketNormalizer()
    timeline = TimelineAnalyzer()
    tickets: list[IncidentTicket] = []
    for segment in segmenter.segment([PageText(number=1, text=text)]):
        ticket = normalizer.normalize(segment)
        tickets.append(ticket.model_copy(update={"timeline": timeline.extract(ticket)}))
    return tickets


@pytest.fixture
def tickets(sample_text: str) -> list[IncidentTicket]:
    return load_tickets(sample_text)


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    settings = Settings(
        use_mock_azure=True,
        data_dir=tmp_path,
        process_inline=True,
        audit_stage_delay_ms=0,
        criteria_path=CRITERIA_PATH,
        sample_pdf_path=REPO_ROOT / "sample-data" / "multi-ticket.pdf",
        sample_text_path=SAMPLE_TEXT,
        prompt_path=REPO_ROOT / "backend" / "app" / "ai" / "prompts" / "audit_system_prompt.txt",
        user_prompt_path=REPO_ROOT / "backend" / "app" / "ai" / "prompts" / "audit_user_prompt.txt",
    )
    return TestClient(create_app(settings))
