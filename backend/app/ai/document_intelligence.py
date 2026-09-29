from __future__ import annotations

import asyncio

from app.models.ticket import DocumentExtraction, PageText
from app.utils.errors import ConfigurationError, InvalidDocumentError, TransientError
from app.utils.retry import with_retries


class AzureDocumentIntelligenceClient:
    def __init__(self, endpoint: str, key: str) -> None:
        if not endpoint or not key:
            raise ConfigurationError("Document Intelligence endpoint and key are required")
        self._endpoint = endpoint
        self._key = key

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
        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential
        except ImportError as exc:
            raise ConfigurationError(
                "Install backend/requirements-azure.txt to call Document Intelligence"
            ) from exc
        client = DocumentIntelligenceClient(self._endpoint, AzureKeyCredential(self._key))
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
