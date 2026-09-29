from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from app.utils.errors import TransientError


async def with_retries(
    operation: Callable[[], Awaitable[object]],
    *,
    retries: int = 3,
    base_delay: float = 0.2,
    retry_on: tuple[type[Exception], ...] = (TransientError,),
) -> object:
    """Retry transient failures with exponential backoff.

    Permanent failures, including invalid model output, propagate immediately.
    """

    attempt = 0
    while True:
        try:
            return await operation()
        except retry_on:
            attempt += 1
            if attempt >= retries:
                raise
            await asyncio.sleep(base_delay * (2 ** (attempt - 1)))
