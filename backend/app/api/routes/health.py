from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_container
from app.services.container import Container

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    use_mock_azure: bool
    criteria_version: str
    service: str


@router.get("/api/health", response_model=HealthResponse)
def health(container: Container = Depends(get_container)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        use_mock_azure=container.settings.use_mock_azure,
        criteria_version=container.criteria.version,
        service="incident-audit",
    )
