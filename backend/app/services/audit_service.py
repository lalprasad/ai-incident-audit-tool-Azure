from __future__ import annotations

import time
from uuid import uuid4

from app.audit.audit_engine import AuditEngine
from app.audit.ticket_extractor import TicketExtractor
from app.config.settings import Settings
from app.models.audit import AuditRecord, AuditSummary
from app.models.job import AuditJob
from app.repositories.protocols import AuditRepository
from app.storage.blob_storage import BlobStore
from app.utils.errors import ConflictError, InvalidDocumentError, InvalidModelOutput, NotFoundError, ScoringError
from app.utils.logging import AuditLogger
from app.utils.time import utcnow


class AuditService:
    def __init__(
        self,
        *,
        settings: Settings,
        repository: AuditRepository,
        blobs: BlobStore,
        extractor: TicketExtractor,
        engine: AuditEngine,
        logger: AuditLogger,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._blobs = blobs
        self._extractor = extractor
        self._engine = engine
        self._log = logger

    async def upload(self, filename: str, content: bytes) -> AuditJob:
        if len(content) > self._settings.max_upload_bytes:
            raise InvalidDocumentError("The PDF is larger than the upload limit.")
        if not content.startswith(b"%PDF"):
            raise InvalidDocumentError("Upload a ServiceNow PDF extract.")
        job_id = str(uuid4())
        blob_name = f"{job_id}.pdf"
        await self._blobs.upload(blob_name, content, "application/pdf")
        now = utcnow()
        job = AuditJob(
            id=job_id,
            filename=filename or "extract.pdf",
            blob_name=blob_name,
            status="Uploaded",
            created_at=now,
            updated_at=now,
        )
        self._repository.save_job(job)
        self._log.event(stage="upload", status="Uploaded", job_id=job_id)
        return job

    def begin_processing(self, job_id: str) -> AuditJob:
        job = self._require_job(job_id)
        if job.status == "Completed":
            raise ConflictError("This extract has already been audited.")
        if job.status not in {"Uploaded", "Failed"}:
            raise ConflictError("This extract is already being audited.")
        if job.status == "Failed":
            for audit_id in list(job.audit_ids):
                self._repository.delete_audit(audit_id)
            job.audit_ids = []
            job.ticket_ids = []
            job.warnings = []
            job.error = None
        job.status = "Extracting"
        job.updated_at = utcnow()
        self._repository.save_job(job)
        return job

    async def process_job(self, job_id: str) -> AuditJob:
        job = self._require_job(job_id)
        started = time.perf_counter()
        try:
            await self._mark(job, "Extracting")
            content = await self._blobs.download(job.blob_name)
            extract_started = time.perf_counter()
            tickets = await self._extractor.extract(content, job.filename)
            job.stage_timings_ms["Extracting"] = _elapsed(extract_started)
            skipped = [ticket for ticket in tickets if not ticket.ticket_id]
            identified = [ticket for ticket in tickets if ticket.ticket_id]
            if skipped:
                job.warnings.append(f"{len(skipped)} record(s) without a ticket ID were skipped.")
            if not identified:
                raise InvalidDocumentError("No incident records were identified in the extract.")
            await self._mark(job, "Tickets identified")
            await self._mark(job, "Auditing")
            audit_started = time.perf_counter()
            known = {audit.ticket_id for audit in self._repository.list_audits()}
            for ticket in identified:
                assert ticket.ticket_id is not None
                if ticket.ticket_id in known:
                    job.warnings.append(
                        f"Duplicate ticket {ticket.ticket_id} stored as a new audit version."
                    )
                try:
                    ticket_started = time.perf_counter()
                    record = await self._engine.audit(
                        ticket,
                        job_id=job.id,
                        version=self._repository.next_version(ticket.ticket_id),
                        audit_id=str(uuid4()),
                    )
                except (InvalidModelOutput, ScoringError):
                    job.warnings.append(
                        f"{ticket.ticket_id} could not be scored because the model output was invalid."
                    )
                    self._log.event(
                        stage="score",
                        status="Failed",
                        job_id=job.id,
                        ticket_id=ticket.ticket_id,
                        error="invalid_model_output",
                    )
                    continue
                self._repository.save_audit(record)
                job.audit_ids.append(record.id)
                job.ticket_ids.append(record.ticket_id)
                known.add(record.ticket_id)
                self._log.event(
                    stage="score",
                    status="Completed",
                    job_id=job.id,
                    ticket_id=record.ticket_id,
                    llm_latency_ms=_elapsed(ticket_started),
                )
            job.stage_timings_ms["Auditing"] = _elapsed(audit_started)
            if not job.audit_ids:
                raise InvalidDocumentError("No tickets could be scored.")
            job.status = "Completed"
            job.error = None
            job.updated_at = utcnow()
            self._repository.save_job(job)
            self._log.event(
                stage="process",
                status="Completed",
                job_id=job.id,
                execution_time_ms=_elapsed(started),
                retry_count=0,
            )
            return job
        except InvalidDocumentError as exc:
            return self._fail(job, str(exc), started)
        except Exception:
            self._log.event(stage="process", status="Failed", job_id=job.id, error="unexpected_error")
            return self._fail(job, "Audit processing failed.", started)

    def list_audits(self) -> list[AuditRecord]:
        return self._repository.list_audits()

    def get_audit(self, audit_id: str) -> AuditRecord:
        audit = self._repository.get_audit(audit_id)
        if audit is None:
            raise NotFoundError("Audit was not found")
        return audit

    def latest_for_ticket(self, ticket_id: str) -> AuditRecord:
        matches = [audit for audit in self._repository.list_audits() if audit.ticket_id == ticket_id]
        if not matches:
            raise NotFoundError("Ticket was not found")
        matches.sort(key=lambda audit: (audit.audit_version, audit.audited_at))
        return matches[-1]

    def get_job(self, job_id: str) -> AuditJob:
        return self._require_job(job_id)

    def list_jobs(self) -> list[AuditJob]:
        return self._repository.list_jobs()

    def override_measure(
        self,
        ticket_id: str,
        measure_id: str,
        *,
        auditor_score: int,
        auditor_comments: str | None,
        override_reason: str,
    ) -> AuditRecord:
        if not override_reason.strip():
            raise ScoringError("An override reason is required")
        audit = self.latest_for_ticket(ticket_id)
        updated = self._engine.apply_override(
            audit,
            measure_id=measure_id,
            auditor_score=auditor_score,
            auditor_comments=auditor_comments,
            override_reason=override_reason.strip(),
        )
        self._repository.save_audit(updated)
        self._log.event(
            stage="override",
            status="Completed",
            ticket_id=ticket_id,
            job_id=updated.job_id,
        )
        return updated

    def review_ticket(self, ticket_id: str, *, decision: str, comments: str | None) -> AuditRecord:
        audit = self.latest_for_ticket(ticket_id)
        updated = self._engine.accept(audit, comments, decision=decision)
        self._repository.save_audit(updated)
        self._log.event(stage="review", status="Completed", ticket_id=ticket_id, job_id=updated.job_id)
        return updated

    def delete_audit(self, audit_id: str) -> None:
        if self._repository.get_audit(audit_id) is None:
            raise NotFoundError("Audit was not found")
        self._repository.delete_audit(audit_id)
        self._log.event(stage="delete", status="Completed", audit_id=audit_id)

    async def delete_job(self, job_id: str) -> None:
        job = self._require_job(job_id)
        for audit_id in job.audit_ids:
            self._repository.delete_audit(audit_id)
        await self._blobs.delete(job.blob_name)
        self._repository.delete_job(job_id)
        self._log.event(stage="delete", status="Completed", job_id=job_id)

    def _require_job(self, job_id: str) -> AuditJob:
        job = self._repository.get_job(job_id)
        if job is None:
            raise NotFoundError("Audit job was not found")
        return job

    async def _mark(self, job: AuditJob, status: str) -> None:
        job.status = status  # type: ignore[assignment]
        job.updated_at = utcnow()
        self._repository.save_job(job)
        self._log.event(stage=status, status=status, job_id=job.id)
        if self._settings.audit_stage_delay_ms > 0:
            import asyncio

            await asyncio.sleep(self._settings.audit_stage_delay_ms / 1000)

    def _fail(self, job: AuditJob, message: str, started: float) -> AuditJob:
        job.status = "Failed"
        job.error = message
        job.updated_at = utcnow()
        self._repository.save_job(job)
        self._log.event(
            stage="process",
            status="Failed",
            job_id=job.id,
            error=message,
            execution_time_ms=_elapsed(started),
        )
        return job


def to_summary(audit: AuditRecord) -> AuditSummary:
    return AuditSummary(
        id=audit.id,
        ticket_id=audit.ticket_id,
        audit_version=audit.audit_version,
        audited_at=audit.audited_at,
        job_id=audit.job_id,
        overall_score=audit.overall_score,
        maximum_score=audit.maximum_score,
        percentage=audit.percentage,
        classification=audit.classification,
        human_review_required=audit.human_review_required,
        auditor_override=audit.auditor_override,
        short_description=audit.ticket.short_description,
        priority=audit.ticket.priority,
        state=audit.ticket.state,
        opened_at=audit.ticket.opened_at,
    )


def _elapsed(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
