#!/usr/bin/env bash
# Azure App Service (Oryx) startup for the Python API + optional SPA.
set -euo pipefail
cd "$(dirname "$0")"
export SERVE_FRONTEND="${SERVE_FRONTEND:-true}"
export STATIC_DIR="${STATIC_DIR:-$(pwd)/static}"
export USE_MOCK_AZURE="${USE_MOCK_AZURE:-false}"
PORT="${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
