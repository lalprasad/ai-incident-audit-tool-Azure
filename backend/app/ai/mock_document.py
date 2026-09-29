from __future__ import annotations

from io import BytesIO

from app.models.ticket import DocumentExtraction, PageText
from app.utils.errors import InvalidDocumentError


class MockDocumentIntelligenceClient:
    """Same analyze() contract as Azure Document Intelligence.

    Reads the PDF text layer with pypdf. The bundled sample is ordinary text,
    so segmentation runs on the extracted words rather than a hidden answer key.
    """

    async def analyze(self, content: bytes, filename: str) -> DocumentExtraction:
        if not content.startswith(b"%PDF"):
            raise InvalidDocumentError("The file is not a PDF.")
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(content))
            pages = [
                PageText(number=index, text=page.extract_text() or "")
                for index, page in enumerate(reader.pages, start=1)
            ]
        except InvalidDocumentError:
            raise
        except Exception as exc:
            raise InvalidDocumentError("The PDF could not be read.") from exc
        if not any(page.text.strip() for page in pages):
            raise InvalidDocumentError("The PDF has no extractable text.")
        return DocumentExtraction(pages=pages)
