from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Protocol

from app.ai.azure_credentials import azure_credential, require_azure_sdk
from app.utils.errors import ConfigurationError, NotFoundError


class BlobStore(Protocol):
    async def upload(self, name: str, data: bytes, content_type: str) -> str: ...

    async def download(self, name: str) -> bytes: ...

    async def delete(self, name: str) -> None: ...


class LocalBlobStorage:
    def __init__(self, root: Path) -> None:
        self._root = root

    async def upload(self, name: str, data: bytes, content_type: str) -> str:
        del content_type
        path = self._path_for(name)

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        await asyncio.to_thread(_write)
        return name

    async def download(self, name: str) -> bytes:
        path = self._path_for(name)
        if not path.exists():
            raise NotFoundError("Uploaded file was not found")
        return await asyncio.to_thread(path.read_bytes)

    async def delete(self, name: str) -> None:
        path = self._path_for(name)

        def _remove() -> None:
            if path.exists():
                path.unlink()

        await asyncio.to_thread(_remove)

    def _path_for(self, name: str) -> Path:
        candidate = (self._root / name).resolve()
        if self._root.resolve() not in candidate.parents and candidate != self._root.resolve():
            raise NotFoundError("Blob name is not valid")
        return candidate


class AzureBlobStorage:
    """Azure Blob Storage via connection string or account URL + managed identity."""

    def __init__(
        self,
        *,
        container: str,
        connection_string: str = "",
        account_url: str = "",
        use_managed_identity: bool = True,
    ) -> None:
        if not connection_string and not account_url:
            raise ConfigurationError(
                "Azure Storage connection string or account URL is required"
            )
        self._connection_string = connection_string
        self._account_url = account_url.rstrip("/")
        self._container = container
        self._use_managed_identity = use_managed_identity and not connection_string

    async def upload(self, name: str, data: bytes, content_type: str) -> str:
        await asyncio.to_thread(self._upload_sync, name, data, content_type)
        return name

    async def download(self, name: str) -> bytes:
        return await asyncio.to_thread(self._download_sync, name)

    async def delete(self, name: str) -> None:
        await asyncio.to_thread(self._delete_sync, name)

    def _service(self):
        require_azure_sdk("azure-storage-blob", "azure.storage.blob")
        from azure.storage.blob import BlobServiceClient

        if self._connection_string:
            return BlobServiceClient.from_connection_string(self._connection_string)
        credential = azure_credential(None)
        return BlobServiceClient(account_url=self._account_url, credential=credential)

    def _client(self, name: str):
        return self._service().get_blob_client(self._container, name)

    def _upload_sync(self, name: str, data: bytes, content_type: str) -> None:
        from azure.storage.blob import ContentSettings

        self._client(name).upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )

    def _download_sync(self, name: str) -> bytes:
        return self._client(name).download_blob().readall()

    def _delete_sync(self, name: str) -> None:
        self._client(name).delete_blob()
