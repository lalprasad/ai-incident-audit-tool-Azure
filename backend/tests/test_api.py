import io

from openpyxl import load_workbook
from pypdf import PdfReader

from app.services.export_service import EXPORT_COLUMNS


def _sample_bytes() -> bytes:
    from pathlib import Path

    return (Path(__file__).resolve().parents[2] / "sample-data" / "multi-ticket.pdf").read_bytes()


def test_health_reports_mock_mode(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["use_mock_azure"] is True
    assert body["criteria_version"] == "1.0.0"


def test_openapi_lists_the_mvp_routes(client) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    expected = [
        "/api/health",
        "/api/audits/upload",
        "/api/audits/{job_id}/process",
        "/api/audits",
        "/api/audits/{audit_id}",
        "/api/tickets/{ticket_id}",
        "/api/tickets/{ticket_id}/review",
        "/api/tickets/{ticket_id}/measures/{measure_id}",
        "/api/dashboard/summary",
        "/api/audits/export",
    ]
    for path in expected:
        assert path in paths


def test_invalid_upload_is_rejected(client) -> None:
    response = client.post(
        "/api/audits/upload",
        files={"file": ("notes.txt", b"not a pdf", "text/plain")},
    )
    assert response.status_code == 400


def test_sample_audit_dashboard_export_and_override(client) -> None:
    content = _sample_bytes()
    reader = PdfReader(io.BytesIO(content))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert extracted.count("INCIDENT NUMBER:") == 8

    uploaded = client.post(
        "/api/audits/upload",
        files={"file": ("multi-ticket.pdf", content, "application/pdf")},
    )
    assert uploaded.status_code == 200
    job_id = uploaded.json()["id"]
    assert uploaded.json()["status"] == "Uploaded"

    processed = client.post(f"/api/audits/{job_id}/process")
    assert processed.status_code == 200
    body = processed.json()
    assert body["status"] == "Completed"
    assert len(body["audit_ids"]) == 8

    listing = client.get("/api/audits")
    assert listing.status_code == 200
    assert listing.json()["total"] == 8

    summary = client.get("/api/dashboard/summary")
    assert summary.status_code == 200
    dashboard = summary.json()
    assert dashboard["total_tickets"] == 8
    assert dashboard["empty"] is False
    assert "Audited 8 tickets" in dashboard["executive_summary"]
    assert dashboard["totals_computed_by"] == "scoring_engine"
    assert len(dashboard["measure_averages"]) == 3
    assert dashboard["score_trend"]

    excellent = client.get("/api/tickets/INC1001")
    assert excellent.status_code == 200
    excellent_body = excellent.json()
    assert excellent_body["classification"] == "Excellent"
    assert excellent_body["percentage"] == 100
    assert excellent_body["human_review_required"] is False
    detail = client.get(f"/api/audits/{excellent_body['id']}")
    assert detail.status_code == 200

    missing = client.get("/api/tickets/INC9999")
    assert missing.status_code == 404

    override = client.put(
        "/api/tickets/INC1001/measures/solutioning",
        json={
            "auditor_score": 3,
            "auditor_comments": "Validation is described, but the change window is vague.",
            "override_reason": "Auditor found the fix description incomplete.",
        },
    )
    assert override.status_code == 200
    overridden = override.json()
    solution = next(item for item in overridden["measures"] if item["measure_id"] == "solutioning")
    assert solution["ai_score"] == 5
    assert solution["final_score"] == 3
    assert overridden["auditor_override"] is True
    assert overridden["percentage"] != 100

    blank = client.put(
        "/api/tickets/INC1001/measures/solutioning",
        json={"auditor_score": 3, "auditor_comments": "", "override_reason": "   "},
    )
    assert blank.status_code == 422

    accepted = client.post(
        "/api/tickets/INC1002/review",
        json={"decision": "accept", "comments": "AI scores match the ticket."},
    )
    assert accepted.status_code == 200
    assert accepted.json()["auditor_review"]["decision"] == "accept"
    assert accepted.json()["auditor_override"] is False

    exported = client.get("/api/audits/export")
    assert exported.status_code == 200
    header = exported.text.splitlines()[0].lstrip("\ufeff")
    assert header.split(",")[0] == EXPORT_COLUMNS[0]
    for column in ("Percentage", "Classification", "Totals Computed By"):
        assert column in header

    workbook_response = client.get("/api/audits/export?format=xlsx")
    workbook = load_workbook(io.BytesIO(workbook_response.content))
    assert workbook["Audits"]["A1"].value == "Ticket ID"
    assert "Executive summary" in workbook["Summary"]["A1"].value

    again = client.post("/api/audits/sample")
    assert again.status_code == 200
    second = client.post(f"/api/audits/{again.json()['id']}/process")
    assert second.status_code == 200
    assert any("Duplicate ticket" in warning for warning in second.json()["warnings"])
    latest = client.get("/api/tickets/INC1001")
    assert latest.json()["audit_version"] == 2
    assert client.get("/api/dashboard/summary").json()["total_tickets"] == 8

    removed = client.delete(f"/api/audits/{excellent_body['id']}")
    assert removed.status_code == 204
    assert client.get(f"/api/audits/{excellent_body['id']}").status_code == 404


def test_corrupt_pdf_fails_the_job(client) -> None:
    uploaded = client.post(
        "/api/audits/upload",
        files={"file": ("broken.pdf", b"%PDF-1.4\nnot really a pdf", "application/pdf")},
    )
    assert uploaded.status_code == 200
    processed = client.post(f"/api/audits/{uploaded.json()['id']}/process")
    assert processed.status_code == 200
    assert processed.json()["status"] == "Failed"
    assert processed.json()["error"]
