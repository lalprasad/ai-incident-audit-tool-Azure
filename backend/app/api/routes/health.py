from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_container
from app.services.container import Container

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    use_mock_azure: bool
    azure_mode: str
    criteria_version: str
    service: str
    openai_deployment: str | None = None


@router.get("/api/health", response_model=HealthResponse)
def health(container: Container = Depends(get_container)) -> HealthResponse:
    settings = container.settings
    if settings.use_mock_azure:
        mode = "mock"
        deployment = None
    else:
        mode = "managed_identity" if (
            settings.azure_use_managed_identity and not settings.azure_openai_api_key
        ) else "api_key"
        deployment = settings.azure_openai_deployment or None
    return HealthResponse(
        status="ok",
        use_mock_azure=settings.use_mock_azure,
        azure_mode=mode,
        criteria_version=container.criteria.version,
        service="incident-audit",
        openai_deployment=deployment,
    )
