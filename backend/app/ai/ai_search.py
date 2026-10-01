from __future__ import annotations

from app.ai.azure_credentials import azure_credential, require_azure_sdk
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
        index_name: str,
        fallback: AuditCriteria,
        key: str = "",
        use_managed_identity: bool = True,
    ) -> None:
        if not endpoint:
            raise ConfigurationError("Azure AI Search endpoint is required")
        if not key and not use_managed_identity:
            raise ConfigurationError("Provide AZURE_SEARCH_KEY or enable managed identity")
        self._endpoint = endpoint
        self._key = key
        self._index_name = index_name
        self._fallback = fallback
        self._use_managed_identity = use_managed_identity and not key

    def get_criteria(self) -> AuditCriteria:
        require_azure_sdk("azure-search-documents", "azure.search.documents")
        from azure.search.documents import SearchClient

        credential = azure_credential(None if self._use_managed_identity else self._key)
        client = SearchClient(self._endpoint, self._index_name, credential)
        results = client.search(search_text="audit criteria", top=1)
        for item in results:
            payload = item.get("criteria") or item.get("content")
            if isinstance(payload, str):
                return AuditCriteria.model_validate_json(payload)
            if isinstance(payload, dict):
                return AuditCriteria.model_validate(payload)
        return self._fallback
