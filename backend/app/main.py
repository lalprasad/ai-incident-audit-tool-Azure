from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import audits, dashboard, health, tickets
from app.config.settings import Settings
from app.services.container import build_container
from app.utils.errors import (
    AuditError,
    ConflictError,
    InvalidDocumentError,
    InvalidModelOutput,
    NotFoundError,
    ScoringError,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO), format="%(message)s")
    container = build_container(settings)
    app = FastAPI(
        title="AI Based Incident Audit Tool",
        version="1.0.0",
        description=(
            "Audits ServiceNow incident extracts. A deterministic scoring engine owns "
            "the total, percentage, and classification. Azure clients are mocked when "
            "USE_MOCK_AZURE=true."
        ),
    )
    app.state.container = container
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(audits.router)
    app.include_router(tickets.router)
    app.include_router(dashboard.router)

    @app.exception_handler(NotFoundError)
    async def not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(InvalidDocumentError)
    async def invalid_document(_: Request, exc: InvalidDocumentError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    async def conflict(_: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(ScoringError)
    async def scoring(_: Request, exc: ScoringError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(InvalidModelOutput)
    async def invalid_model(_: Request, exc: InvalidModelOutput) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(AuditError)
    async def audit_error(_: Request, exc: AuditError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return app


app = create_app()
