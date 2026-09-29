from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
APP_DIR = BACKEND_DIR / "app"


class Settings(BaseSettings):
    use_mock_azure: bool = True
    data_dir: Path = BACKEND_DIR / ".data"
    criteria_path: Path = APP_DIR / "config" / "audit_criteria.json"
    prompt_path: Path = APP_DIR / "ai" / "prompts" / "audit_system_prompt.txt"
    user_prompt_path: Path = APP_DIR / "ai" / "prompts" / "audit_user_prompt.txt"
    sample_pdf_path: Path = REPO_ROOT / "sample-data" / "multi-ticket.pdf"
    sample_text_path: Path = REPO_ROOT / "sample-data" / "multi-ticket.txt"
    frontend_origins: str = "http://127.0.0.1:43123,http://localhost:43123"
    audit_stage_delay_ms: int = 0
    process_inline: bool = False
    max_upload_bytes: int = 20 * 1024 * 1024
    log_level: str = "INFO"
    ai_model_name: str = "mock-deterministic"
    model_version: str = "mock-rules-1.0.0"

    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_document_intelligence_endpoint: str = ""
    azure_document_intelligence_key: str = ""
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "incident-audits"
    azure_cosmos_endpoint: str = ""
    azure_cosmos_key: str = ""
    azure_cosmos_database: str = "incident-audit"
    azure_cosmos_container: str = "audits"
    azure_search_endpoint: str = ""
    azure_search_key: str = ""
    azure_search_index: str = "audit-criteria"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.frontend_origins.split(",") if item.strip()]
