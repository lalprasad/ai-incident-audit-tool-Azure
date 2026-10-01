import pytest

from app.config.settings import Settings
from app.utils.errors import ConfigurationError


def test_live_azure_requires_core_endpoints() -> None:
    settings = Settings(
        use_mock_azure=False,
        azure_use_managed_identity=True,
        azure_openai_endpoint="",
        azure_openai_deployment="gpt-4o-mini",
    )
    with pytest.raises(ConfigurationError, match="AZURE_OPENAI_ENDPOINT"):
        settings.validate_live_azure()


def test_live_azure_accepts_managed_identity_without_keys() -> None:
    settings = Settings(
        use_mock_azure=False,
        azure_use_managed_identity=True,
        azure_openai_endpoint="https://example.openai.azure.com/",
        azure_openai_deployment="gpt-4o-mini",
        azure_document_intelligence_endpoint="https://example.cognitiveservices.azure.com/",
        azure_storage_account_url="https://example.blob.core.windows.net",
        azure_cosmos_endpoint="https://example.documents.azure.com:443/",
    )
    settings.validate_live_azure()


def test_sample_paths_resolve_from_repo_layout() -> None:
    settings = Settings()
    assert settings.sample_pdf_path.exists()
    assert settings.sample_text_path.exists()
    assert settings.sample_pdf_path.name == "multi-ticket.pdf"
