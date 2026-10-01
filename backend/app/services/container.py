from __future__ import annotations

from dataclasses import dataclass

from app.ai.ai_search import AzureSearchCriteriaRetriever, LocalJsonCriteriaRetriever
from app.ai.azure_openai import AzureOpenAIAuditClient
from app.ai.document_intelligence import AzureDocumentIntelligenceClient
from app.ai.mock_document import MockDocumentIntelligenceClient
from app.ai.mock_openai import MockAuditModel
from app.ai.protocols import AuditModel, CriteriaRetriever, DocumentClient
from app.audit.audit_engine import AuditEngine
from app.audit.evidence_analyzer import EvidenceAnalyzer
from app.audit.scoring_engine import ScoringEngine
from app.audit.ticket_extractor import TicketExtractor
from app.audit.ticket_normalizer import TicketNormalizer
from app.audit.ticket_segmenter import TicketSegmenter
from app.audit.timeline_analyzer import TimelineAnalyzer
from app.config.criteria_loader import load_criteria
from app.config.settings import Settings
from app.models.criteria import AuditCriteria
from app.repositories.file_audit_repository import FileAuditRepository
from app.repositories.protocols import AuditRepository
from app.services.audit_service import AuditService
from app.storage.blob_storage import AzureBlobStorage, BlobStore, LocalBlobStorage
from app.storage.cosmos_repository import CosmosAuditRepository
from app.utils.logging import AuditLogger


@dataclass
class Container:
    settings: Settings
    criteria: AuditCriteria
    repository: AuditRepository
    blobs: BlobStore
    audits: AuditService
    system_prompt: str


def build_container(settings: Settings) -> Container:
    criteria = _criteria(settings)
    scoring = ScoringEngine(criteria)
    system_prompt = settings.prompt_path.read_text(encoding="utf-8")
    user_prompt = settings.user_prompt_path.read_text(encoding="utf-8")
    if settings.use_mock_azure:
        documents: DocumentClient = MockDocumentIntelligenceClient()
        model: AuditModel = MockAuditModel()
        repository: AuditRepository = FileAuditRepository(settings.data_dir / "store.json")
        blobs: BlobStore = LocalBlobStorage(settings.data_dir / "blobs")
        ai_model = settings.ai_model_name
        model_version = settings.model_version
    else:
        settings.validate_live_azure()
        mi = settings.azure_use_managed_identity
        documents = AzureDocumentIntelligenceClient(
            settings.azure_document_intelligence_endpoint,
            settings.azure_document_intelligence_key,
            use_managed_identity=mi,
        )
        model = AzureOpenAIAuditClient(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version,
            use_managed_identity=mi,
        )
        repository = CosmosAuditRepository(
            endpoint=settings.azure_cosmos_endpoint,
            key=settings.azure_cosmos_key,
            database=settings.azure_cosmos_database,
            container=settings.azure_cosmos_container,
            use_managed_identity=mi,
        )
        blobs = AzureBlobStorage(
            container=settings.azure_storage_container,
            connection_string=settings.azure_storage_connection_string,
            account_url=settings.azure_storage_account_url,
            use_managed_identity=mi,
        )
        ai_model = settings.azure_openai_deployment
        model_version = settings.azure_openai_api_version
    engine = AuditEngine(
        model=model,
        scoring=scoring,
        evidence=EvidenceAnalyzer(scoring),
        criteria=criteria,
        timeline=TimelineAnalyzer(),
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        ai_model=ai_model,
        model_version=model_version,
    )
    audits = AuditService(
        settings=settings,
        repository=repository,
        blobs=blobs,
        extractor=TicketExtractor(documents, TicketSegmenter(), TicketNormalizer()),
        engine=engine,
        logger=AuditLogger(),
    )
    return Container(
        settings=settings,
        criteria=criteria,
        repository=repository,
        blobs=blobs,
        audits=audits,
        system_prompt=system_prompt,
    )


def _criteria(settings: Settings) -> AuditCriteria:
    local = load_criteria(settings.criteria_path)
    retriever: CriteriaRetriever
    if settings.use_mock_azure or not settings.azure_search_endpoint:
        retriever = LocalJsonCriteriaRetriever(local)
    else:
        retriever = AzureSearchCriteriaRetriever(
            endpoint=settings.azure_search_endpoint,
            key=settings.azure_search_key,
            index_name=settings.azure_search_index,
            fallback=local,
            use_managed_identity=settings.azure_use_managed_identity,
        )
    return retriever.get_criteria()
