from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Protocol

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
    def __init__(self, connection_string: str, container: str) -> None:
        if not connection_string:
            raise ConfigurationError("Azure Storage connection string is required")
        self._connection_string = connection_string
        self._container = container

    async def upload(self, name: str, data: bytes, content_type: str) -> str:
        await asyncio.to_thread(self._upload_sync, name, data, content_type)
        return name

    async def download(self, name: str) -> bytes:
        return await asyncio.to_thread(self._download_sync, name)

    async def delete(self, name: str) -> None:
        await asyncio.to_thread(self._delete_sync, name)

    def _client(self, name: str):
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError as exc:
            raise ConfigurationError("Install backend/requirements-azure.txt to use Azure Blob Storage") from exc
        service = BlobServiceClient.from_connection_string(self._connection_string)
        return service.get_blob_client(self._container, name)

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
