"""A synchronous view of an async object, for use from the worker thread.

The run pipeline is deliberately synchronous: it makes blocking HTTP calls to model
providers, one after another, and reads that way. The store and repository are async
because they sit behind asyncpg. Rewriting the pipeline in async would gain nothing -
there is no concurrency to exploit inside a single run - and would put blocking
provider calls on the event loop serving the API.

So the worker runs in a thread and reaches the database through this facade, which
submits each coroutine to the API's event loop and waits. One loop, one engine, one
connection pool, and no async colouring spreading through the pipeline.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any

DEFAULT_TIMEOUT = 60.0


class SyncFacade:
    """Wraps an object whose methods are coroutines and exposes them as blocking calls."""

    def __init__(
        self,
        target: Any,
        loop: asyncio.AbstractEventLoop,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._target = target
        self._loop = loop
        self._timeout = timeout

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._target, name)
        if not callable(attr):
            return attr

        def call(*args: Any, **kwargs: Any) -> Any:
            result = attr(*args, **kwargs)
            if not inspect.isawaitable(result):
                return result
            future = asyncio.run_coroutine_threadsafe(result, self._loop)
            return future.result(timeout=self._timeout)

        return call
