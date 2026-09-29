from __future__ import annotations

from app.models.criteria import AuditCriteria
from app.utils.errors import ConfigurationError


class LocalJsonCriteriaRetriever:
    def __init__(self, criteria: AuditCriteria) -> None:
        self._criteria = criteria

    def get_criteria(self) -> AuditCriteria:
        return self._criteria


class AzureSearchCriteriaRetriever:
    """Optional live retriever. Falls back to the local rubric if the index is empty."""

    def __init__(
        self,
        *,
        endpoint: str,
        key: str,
        index_name: str,
        fallback: AuditCriteria,
    ) -> None:
        if not endpoint or not key:
            raise ConfigurationError("Azure AI Search endpoint and key are required")
        self._endpoint = endpoint
        self._key = key
        self._index_name = index_name
        self._fallback = fallback

    def get_criteria(self) -> AuditCriteria:
        try:
            from azure.core.credentials import AzureKeyCredential
            from azure.search.documents import SearchClient
        except ImportError as exc:
            raise ConfigurationError(
                "Install backend/requirements-azure.txt to query Azure AI Search"
            ) from exc
        client = SearchClient(self._endpoint, self._index_name, AzureKeyCredential(self._key))
        results = client.search(search_text="audit criteria", top=1)
        for item in results:
            payload = item.get("criteria") or item.get("content")
            if isinstance(payload, str):
                return AuditCriteria.model_validate_json(payload)
            if isinstance(payload, dict):
                return AuditCriteria.model_validate(payload)
        return self._fallback
