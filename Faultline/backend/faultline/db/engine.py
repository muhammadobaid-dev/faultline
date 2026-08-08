"""Database connection.

One environment variable holds the connection string exactly as Neon prints it.
Everything that needs a different form of it derives that form here, so there is a
single value to manage and no chance of a password being retyped wrongly.

Neon's `?sslmode=require` is libpq syntax. asyncpg rejects it and wants TLS passed
as a connect argument instead, and Alembic wants a synchronous URL. Both are derived
from the same source below.
"""

from __future__ import annotations

import logging
import os
import ssl
from functools import lru_cache
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

log = logging.getLogger("faultline.db")

ENV_VAR = "FAULTLINE_DATABASE_URL"

# Stripped rather than passed through: these are libpq keywords that asyncpg does
# not accept as query parameters.
_LIBPQ_ONLY = {"sslmode", "channel_binding", "options", "target_session_attrs"}


class MissingDatabaseURL(RuntimeError):
    pass


def raw_url() -> str:
    url = os.environ.get(ENV_VAR, "").strip()
    if not url:
        raise MissingDatabaseURL(
            f"{ENV_VAR} is not set. Use the connection string exactly as Neon prints it."
        )
    return url


def _split_query(url: str) -> tuple[str, dict[str, str]]:
    parts = urlsplit(url)
    params: dict[str, str] = {}
    for chunk in parts.query.split("&"):
        if not chunk:
            continue
        key, _, value = chunk.partition("=")
        params[key] = value
    keep = "&".join(f"{k}={v}" for k, v in params.items() if k not in _LIBPQ_ONLY)
    cleaned = urlunsplit((parts.scheme, parts.netloc, parts.path, keep, parts.fragment))
    return cleaned, params


def async_url(url: str | None = None) -> str:
    """asyncpg form: our own scheme, and no libpq-only query parameters."""
    cleaned, _ = _split_query(url or raw_url())
    scheme, _, rest = cleaned.partition("://")
    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+asyncpg"
    return f"{scheme}://{rest}"


def requires_tls(url: str | None = None) -> bool:
    _, params = _split_query(url or raw_url())
    return params.get("sslmode", "").lower() in {"require", "verify-ca", "verify-full"}


@lru_cache(maxsize=1)
def engine() -> AsyncEngine:
    url = raw_url()
    connect_args: dict[str, object] = {}
    if requires_tls(url):
        connect_args["ssl"] = ssl.create_default_context()

    return create_async_engine(
        async_url(url),
        connect_args=connect_args,
        # Neon's free compute sleeps after five minutes and wakes in about half a
        # second. Recycling below that window avoids handing out a connection the
        # far end has already dropped.
        pool_pre_ping=True,
        pool_recycle=240,
        pool_size=5,
        max_overflow=5,
        echo=False,
    )


def session_factory() -> sessionmaker[AsyncSession]:
    return sessionmaker(engine(), class_=AsyncSession, expire_on_commit=False)
