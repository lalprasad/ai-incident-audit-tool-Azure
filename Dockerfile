# Single-container Azure App Service / Container Apps image.
# Builds the React UI into backend/static and serves API + SPA together.
FROM node:22-bookworm-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_BASE_URL=
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    USE_MOCK_AZURE=false \
    SERVE_FRONTEND=true \
    STATIC_DIR=/app/backend/static \
    PORT=8000

WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements-azure.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt -r backend/requirements-azure.txt

COPY backend ./backend
COPY sample-data ./sample-data
COPY --from=frontend /frontend/dist ./backend/static

WORKDIR /app/backend
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/api/health" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
