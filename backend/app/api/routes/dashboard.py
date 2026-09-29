from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_container
from app.models.criteria import CriteriaDocument
from app.models.dashboard import DashboardSummary
from app.services.container import Container
from app.services.dashboard_service import build_summary

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(container: Container = Depends(get_container)) -> DashboardSummary:
    return build_summary(container.audits.list_audits(), container.criteria)


@router.get("/criteria", response_model=CriteriaDocument)
def criteria(container: Container = Depends(get_container)) -> CriteriaDocument:
    rubric = container.criteria
    return CriteriaDocument(
        version=rubric.version,
        prompt_version=rubric.prompt_version,
        measures=rubric.measures,
        classification=rubric.classification,
        confidence_bands=rubric.confidence_bands,
    )
