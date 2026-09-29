from __future__ import annotations

from app.audit.ticket_normalizer import TicketNormalizer
from app.audit.ticket_segmenter import TicketSegmenter
from app.ai.protocols import DocumentClient
from app.models.ticket import IncidentTicket


class TicketExtractor:
    def __init__(
        self,
        documents: DocumentClient,
        segmenter: TicketSegmenter,
        normalizer: TicketNormalizer,
    ) -> None:
        self._documents = documents
        self._segmenter = segmenter
        self._normalizer = normalizer

    async def extract(self, content: bytes, filename: str) -> list[IncidentTicket]:
        extraction = await self._documents.analyze(content, filename)
        segments = self._segmenter.segment(extraction.pages)
        return [self._normalizer.normalize(segment) for segment in segments]
