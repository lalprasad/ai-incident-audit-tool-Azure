from __future__ import annotations

import json
import threading
from pathlib import Path

from app.models.audit import AuditRecord
from app.models.job import AuditJob


class FileAuditRepository:
    """Cosmos-shaped JSON documents on disk. Same methods as the Cosmos repository."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()

    def save_audit(self, audit: AuditRecord) -> AuditRecord:
        with self._lock:
            data = self._load()
            data["audits"][audit.id] = audit.model_dump(mode="json")
            self._write(data)
        return audit

    def get_audit(self, audit_id: str) -> AuditRecord | None:
        with self._lock:
            raw = self._load()["audits"].get(audit_id)
        return AuditRecord.model_validate(raw) if raw else None

    def list_audits(self) -> list[AuditRecord]:
        with self._lock:
            raw_items = list(self._load()["audits"].values())
        audits = [AuditRecord.model_validate(item) for item in raw_items]
        audits.sort(key=lambda audit: audit.audited_at, reverse=True)
        return audits

    def delete_audit(self, audit_id: str) -> None:
        with self._lock:
            data = self._load()
            data["audits"].pop(audit_id, None)
            self._write(data)

    def next_version(self, ticket_id: str) -> int:
        versions = [audit.audit_version for audit in self.list_audits() if audit.ticket_id == ticket_id]
        return (max(versions) if versions else 0) + 1

    def save_job(self, job: AuditJob) -> AuditJob:
        with self._lock:
            data = self._load()
            data["jobs"][job.id] = job.model_dump(mode="json")
            self._write(data)
        return job

    def get_job(self, job_id: str) -> AuditJob | None:
        with self._lock:
            raw = self._load()["jobs"].get(job_id)
        return AuditJob.model_validate(raw) if raw else None

    def list_jobs(self) -> list[AuditJob]:
        with self._lock:
            raw_items = list(self._load()["jobs"].values())
        jobs = [AuditJob.model_validate(item) for item in raw_items]
        jobs.sort(key=lambda job: job.created_at, reverse=True)
        return jobs

    def delete_job(self, job_id: str) -> None:
        with self._lock:
            data = self._load()
            data["jobs"].pop(job_id, None)
            self._write(data)

    def _load(self) -> dict:
        if not self._path.exists():
            return {"audits": {}, "jobs": {}}
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _write(self, data: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data), encoding="utf-8")
        temporary.replace(self._path)
