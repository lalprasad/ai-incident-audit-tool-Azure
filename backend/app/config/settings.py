from __future__ import annotations

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
APP_DIR = BACKEND_DIR / "app"


def _first_existing(*candidates: Path) -> Path:
    """Prefer a real file (Docker/repo layout) over a missing default path."""
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


class Settings(BaseSettings):
    use_mock_azure: bool = True
    data_dir: Path = BACKEND_DIR / ".data"
    criteria_path: Path = APP_DIR / "config" / "audit_criteria.json"
    prompt_path: Path = APP_DIR / "ai" / "prompts" / "audit_system_prompt.txt"
    user_prompt_path: Path = APP_DIR / "ai" / "prompts" / "audit_user_prompt.txt"
    # Repo layout: <root>/sample-data. Zip/App Service: <backend>/sample-data.
    sample_pdf_path: Path = _first_existing(
        REPO_ROOT / "sample-data" / "multi-ticket.pdf",
        BACKEND_DIR / "sample-data" / "multi-ticket.pdf",
    )
    sample_text_path: Path = _first_existing(
        REPO_ROOT / "sample-data" / "multi-ticket.txt",
        BACKEND_DIR / "sample-data" / "multi-ticket.txt",
    )
    frontend_origins: str = "http://127.0.0.1:43123,http://localhost:43123"
    serve_frontend: bool = False
    static_dir: Path = BACKEND_DIR / "static"
    audit_stage_delay_ms: int = 0
    process_inline: bool = False
    max_upload_bytes: int = 20 * 1024 * 1024
    log_level: str = "INFO"
    ai_model_name: str = "mock-deterministic"
    model_version: str = "mock-rules-1.0.0"

    # Azure AI / OpenAI (also works with Azure AI Foundry project endpoints)
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_version: str = "2024-10-21"

    azure_document_intelligence_endpoint: str = ""
    azure_document_intelligence_key: str = ""

    # Prefer account URL + managed identity in Azure; connection string still supported
    azure_storage_connection_string: str = ""
    azure_storage_account_url: str = ""
    azure_storage_container: str = "incident-audits"

    azure_cosmos_endpoint: str = ""
    azure_cosmos_key: str = ""
    azure_cosmos_database: str = "incident-audit"
    azure_cosmos_container: str = "audits"

    azure_search_endpoint: str = ""
    azure_search_key: str = ""
    azure_search_index: str = "audit-criteria"

    # When true (default in live mode with empty keys), use DefaultAzureCredential / MI
    azure_use_managed_identity: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator(
        "use_mock_azure",
        "serve_frontend",
        "process_inline",
        "azure_use_managed_identity",
        mode="before",
    )
    @classmethod
    def _parse_bool(cls, value: object) -> object:
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "yes", "on"}:
                return True
            if lowered in {"0", "false", "no", "off"}:
                return False
        return value

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.frontend_origins.split(",") if item.strip()]

    @property
    def live_azure(self) -> bool:
        return not self.use_mock_azure

    def validate_live_azure(self) -> None:
        """Fail fast with a clear message when live Azure AI config is incomplete."""
        from app.utils.errors import ConfigurationError

        missing: list[str] = []
        if not self.azure_openai_endpoint:
            missing.append("AZURE_OPENAI_ENDPOINT")
        if not self.azure_openai_deployment:
            missing.append("AZURE_OPENAI_DEPLOYMENT")
        if not self.azure_openai_api_key and not self.azure_use_managed_identity:
            missing.append("AZURE_OPENAI_API_KEY (or enable AZURE_USE_MANAGED_IDENTITY)")
        if not self.azure_document_intelligence_endpoint:
            missing.append("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        if not self.azure_document_intelligence_key and not self.azure_use_managed_identity:
            missing.append("AZURE_DOCUMENT_INTELLIGENCE_KEY")
        if not self.azure_storage_connection_string and not self.azure_storage_account_url:
            missing.append("AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_ACCOUNT_URL")
        if not self.azure_cosmos_endpoint:
            missing.append("AZURE_COSMOS_ENDPOINT")
        if not self.azure_cosmos_key and not self.azure_use_managed_identity:
            missing.append("AZURE_COSMOS_KEY")
        if missing:
            raise ConfigurationError(
                "Live Azure AI mode requires: " + ", ".join(missing)
            )
