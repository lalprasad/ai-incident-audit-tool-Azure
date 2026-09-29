from __future__ import annotations

from app.models.audit import AuditRecord
from app.models.job import AuditJob
from app.utils.errors import ConfigurationError


class CosmosAuditRepository:
    """Same repository contract as the local JSON store. Partition key is ticket_id."""

    def __init__(self, *, endpoint: str, key: str, database: str, container: str) -> None:
        if not endpoint or not key:
            raise ConfigurationError("Cosmos endpoint and key are required")
        self._endpoint = endpoint
        self._key = key
        self._database = database
        self._container = container

    def save_audit(self, audit: AuditRecord) -> AuditRecord:
        document = audit.model_dump(mode="json")
        document["id"] = audit.id
        document["kind"] = "audit"
        document["partition"] = audit.ticket_id
        self._container_client().upsert_item(document)
        return audit

    def get_audit(self, audit_id: str) -> AuditRecord | None:
        query = "SELECT * FROM c WHERE c.id = @id AND c.kind = 'audit'"
        items = self._query_audits(query, [{"name": "@id", "value": audit_id}])
        return items[0] if items else None

    def list_audits(self) -> list[AuditRecord]:
        return self._query_audits("SELECT * FROM c WHERE c.kind = 'audit'", [])

    def delete_audit(self, audit_id: str) -> None:
        found = self.get_audit(audit_id)
        if found is None:
            return
        self._container_client().delete_item(item=audit_id, partition_key=found.ticket_id)

    def next_version(self, ticket_id: str) -> int:
        versions = [audit.audit_version for audit in self.list_audits() if audit.ticket_id == ticket_id]
        return (max(versions) if versions else 0) + 1

    def save_job(self, job: AuditJob) -> AuditJob:
        document = job.model_dump(mode="json")
        document["id"] = job.id
        document["kind"] = "job"
        document["ticket_id"] = job.id
        self._container_client().upsert_item(document)
        return job

    def get_job(self, job_id: str) -> AuditJob | None:
        try:
            raw = self._container_client().read_item(item=job_id, partition_key=job_id)
        except Exception:
            return None
        if raw.get("kind") != "job":
            return None
        raw.pop("kind", None)
        raw.pop("ticket_id", None)
        return AuditJob.model_validate(raw)

    def list_jobs(self) -> list[AuditJob]:
        items = list(
            self._container_client().query_items(
                query="SELECT * FROM c WHERE c.kind = 'job'",
                enable_cross_partition_query=True,
            )
        )
        jobs = []
        for raw in items:
            raw.pop("kind", None)
            raw.pop("ticket_id", None)
            jobs.append(AuditJob.model_validate(raw))
        jobs.sort(key=lambda job: job.created_at, reverse=True)
        return jobs

    def delete_job(self, job_id: str) -> None:
        try:
            self._container_client().delete_item(item=job_id, partition_key=job_id)
        except Exception:
            return

    def _query_audits(self, query: str, parameters: list[dict]) -> list[AuditRecord]:
        items = list(
            self._container_client().query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )
        audits = []
        for raw in items:
            raw.pop("kind", None)
            raw.pop("partition", None)
            audits.append(AuditRecord.model_validate(raw))
        audits.sort(key=lambda audit: audit.audited_at, reverse=True)
        return audits

    def _container_client(self):
        try:
            from azure.cosmos import CosmosClient
        except ImportError as exc:
            raise ConfigurationError("Install backend/requirements-azure.txt to use Cosmos DB") from exc
        client = CosmosClient(self._endpoint, credential=self._key)
        database = client.get_database_client(self._database)
        return database.get_container_client(self._container)
