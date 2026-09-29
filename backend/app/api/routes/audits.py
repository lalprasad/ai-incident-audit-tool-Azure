from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, Response, UploadFile

from app.api.deps import get_container
from app.models.audit import AuditList, AuditRecord
from app.models.job import AuditJob, JobList
from app.services.audit_service import to_summary
from app.services.container import Container
from app.services.dashboard_service import build_summary, latest_audits
from app.services.export_service import render_csv, render_xlsx
from app.utils.errors import InvalidDocumentError

router = APIRouter(prefix="/api/audits", tags=["audits"])


@router.post("/upload", response_model=AuditJob)
async def upload_pdf(
    file: UploadFile = File(...),
    container: Container = Depends(get_container),
) -> AuditJob:
    content = await file.read()
    return await container.audits.upload(file.filename or "extract.pdf", content)


@router.post("/sample", response_model=AuditJob)
async def upload_sample(container: Container = Depends(get_container)) -> AuditJob:
    path = container.settings.sample_pdf_path
    if not path.exists():
        raise InvalidDocumentError("Sample PDF is missing. Run python sample-data/build_pdf.py.")
    return await container.audits.upload(path.name, path.read_bytes())


@router.get("/export")
def export_audits(
    format: str = "csv",
    latest_only: bool = True,
    container: Container = Depends(get_container),
) -> Response:
    audits = container.audits.list_audits()
    if latest_only:
        audits = latest_audits(audits)
    summary = build_summary(container.audits.list_audits(), container.criteria)
    if format == "xlsx":
        payload = render_xlsx(audits, summary)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "incident-audit.xlsx"
    else:
        payload = render_csv(audits)
        media = "text/csv; charset=utf-8"
        filename = "incident-audit.csv"
    return Response(
        content=payload,
        media_type=media,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/jobs", response_model=JobList)
def list_jobs(container: Container = Depends(get_container)) -> JobList:
    items = container.audits.list_jobs()
    return JobList(items=items, total=len(items))


@router.get("/jobs/{job_id}", response_model=AuditJob)
def get_job(job_id: str, container: Container = Depends(get_container)) -> AuditJob:
    return container.audits.get_job(job_id)


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(job_id: str, container: Container = Depends(get_container)) -> Response:
    await container.audits.delete_job(job_id)
    return Response(status_code=204)


@router.post("/{job_id}/process", response_model=AuditJob)
async def process_audit(
    job_id: str,
    background: BackgroundTasks,
    container: Container = Depends(get_container),
) -> AuditJob:
    job = container.audits.begin_processing(job_id)
    if container.settings.process_inline:
        return await container.audits.process_job(job_id)
    background.add_task(container.audits.process_job, job_id)
    return job


@router.get("", response_model=AuditList)
def list_audits(container: Container = Depends(get_container)) -> AuditList:
    items = [to_summary(audit) for audit in container.audits.list_audits()]
    return AuditList(items=items, total=len(items))


@router.get("/{audit_id}", response_model=AuditRecord)
def get_audit(audit_id: str, container: Container = Depends(get_container)) -> AuditRecord:
    return container.audits.get_audit(audit_id)


@router.delete("/{audit_id}", status_code=204)
def delete_audit(audit_id: str, container: Container = Depends(get_container)) -> Response:
    container.audits.delete_audit(audit_id)
    return Response(status_code=204)
