from __future__ import annotations

from typing import Any

from app.utils.errors import ConfigurationError


def require_azure_sdk(package: str, import_name: str | None = None) -> None:
    """Raise a clear ConfigurationError when optional Azure packages are missing."""
    module = import_name or package
    try:
        __import__(module)
    except ImportError as exc:
        raise ConfigurationError(
            f"Install backend/requirements-azure.txt to use {package} "
            "(Azure AI live mode)."
        ) from exc


def azure_credential(api_key: str | None = None) -> Any:
    """Return an AzureKeyCredential when a key is set, else DefaultAzureCredential."""
    if api_key:
        require_azure_sdk("azure-core", "azure.core.credentials")
        from azure.core.credentials import AzureKeyCredential

        return AzureKeyCredential(api_key)

    require_azure_sdk("azure-identity", "azure.identity")
    from azure.identity import DefaultAzureCredential

    return DefaultAzureCredential(exclude_interactive_browser_credential=True)


def openai_token_provider():
    """Bearer token provider for Azure OpenAI / Azure AI Foundry with managed identity."""
    require_azure_sdk("azure-identity", "azure.identity")
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider

    return get_bearer_token_provider(
        DefaultAzureCredential(exclude_interactive_browser_credential=True),
        "https://cognitiveservices.azure.com/.default",
    )
