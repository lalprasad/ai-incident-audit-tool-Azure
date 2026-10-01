from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import audits, dashboard, health, tickets
from app.config.settings import Settings
from app.services.container import build_container
from app.utils.errors import (
    AuditError,
    ConfigurationError,
    ConflictError,
    InvalidDocumentError,
    InvalidModelOutput,
    NotFoundError,
    ScoringError,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(message)s",
    )
    container = build_container(settings)
    app = FastAPI(
        title="AI Based Incident Audit Tool",
        version="1.0.0",
        description=(
            "Audits ServiceNow incident extracts with Azure AI (Document Intelligence "
            "+ Azure OpenAI). Deterministic scoring owns totals. Set USE_MOCK_AZURE=true "
            "for local mock mode."
        ),
    )
    app.state.container = container
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins or ["*"],
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

    @app.exception_handler(ConfigurationError)
    async def configuration_error(_: Request, exc: ConfigurationError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(AuditError)
    async def audit_error(_: Request, exc: AuditError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    _mount_frontend(app, settings)
    return app


def _mount_frontend(app: FastAPI, settings: Settings) -> None:
    static_dir = Path(settings.static_dir)
    if not settings.serve_frontend and not (static_dir / "index.html").exists():
        return
    if not static_dir.exists():
        return
    assets = static_dir / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/")
    async def spa_index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        # Never shadow the API or OpenAPI routes.
        if full_path.startswith("api/") or full_path in {"docs", "redoc", "openapi.json"}:
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        candidate = (static_dir / full_path).resolve()
        static_root = static_dir.resolve()
        if candidate.is_file() and (
            candidate == static_root or static_root in candidate.parents
        ):
            return FileResponse(candidate)
        return FileResponse(static_dir / "index.html")


app = create_app()
