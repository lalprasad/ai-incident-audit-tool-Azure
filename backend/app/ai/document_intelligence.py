from __future__ import annotations

import asyncio

from app.ai.azure_credentials import azure_credential, require_azure_sdk
from app.models.ticket import DocumentExtraction, PageText
from app.utils.errors import ConfigurationError, InvalidDocumentError, TransientError
from app.utils.retry import with_retries


class AzureDocumentIntelligenceClient:
    def __init__(
        self,
        endpoint: str,
        key: str = "",
        *,
        use_managed_identity: bool = True,
    ) -> None:
        if not endpoint:
            raise ConfigurationError("Document Intelligence endpoint is required")
        if not key and not use_managed_identity:
            raise ConfigurationError(
                "Provide AZURE_DOCUMENT_INTELLIGENCE_KEY or enable managed identity"
            )
        self._endpoint = endpoint.rstrip("/")
        self._key = key
        self._use_managed_identity = use_managed_identity and not key

    async def analyze(self, content: bytes, filename: str) -> DocumentExtraction:
        del filename

        async def _call() -> DocumentExtraction:
            try:
                return await asyncio.to_thread(self._analyze_sync, content)
            except (ConfigurationError, InvalidDocumentError):
                raise
            except Exception as exc:
                if _transient(exc):
                    raise TransientError("Document Intelligence request failed") from exc
                raise InvalidDocumentError("Document Intelligence could not read the PDF") from exc

        return await with_retries(_call)  # type: ignore[return-value]

    def _analyze_sync(self, content: bytes) -> DocumentExtraction:
        require_azure_sdk("azure-ai-documentintelligence", "azure.ai.documentintelligence")
        from azure.ai.documentintelligence import DocumentIntelligenceClient

        credential = azure_credential(None if self._use_managed_identity else self._key)
        client = DocumentIntelligenceClient(self._endpoint, credential)
        poller = client.begin_analyze_document(
            "prebuilt-layout",
            body=content,
            content_type="application/pdf",
        )
        result = poller.result()
        pages: list[PageText] = []
        for page in getattr(result, "pages", None) or []:
            lines = [
                getattr(line, "content", "") or ""
                for line in (getattr(page, "lines", None) or [])
            ]
            pages.append(
                PageText(
                    number=int(getattr(page, "page_number", len(pages) + 1)),
                    text="\n".join(line for line in lines if line),
                )
            )
        if not pages and getattr(result, "content", None):
            pages.append(PageText(number=1, text=result.content))
        if not any(page.text.strip() for page in pages):
            raise InvalidDocumentError("Document Intelligence returned no text")
        return DocumentExtraction(pages=pages)


def _transient(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    if status is None:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
    if isinstance(status, int) and status >= 500:
        return True
    name = exc.__class__.__name__.lower()
    return "timeout" in name or "service" in name
