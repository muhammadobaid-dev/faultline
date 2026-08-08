"""Ordered API keys with automatic failover.

We prefer a development key so iteration does not draw down the production
allowance, but a preferred key can be dead - a Google Cloud project can be denied
access while still answering metadata calls. Both `ListModels` and `countTokens`
return 200 on a project that cannot generate, so no cheap pre-flight check can tell
a live key from a dead one.

The reliable signal is the real call. This ring tries keys in order and retires one
permanently for the process when the provider says its project is denied, so a dead
key costs exactly one rejected request and never silently swallows a run.
"""

from __future__ import annotations

import logging

log = logging.getLogger("faultline.keys")


class NoUsableKey(RuntimeError):
    pass


class KeyRing:
    """Ordered candidate keys. Values are never logged, only their variable names."""

    def __init__(self, candidates: list[tuple[str, str]]) -> None:
        self._candidates = [(name, key) for name, key in candidates if key]
        if not self._candidates:
            raise NoUsableKey("no Gemini API key found in the environment")
        self._index = 0
        self._announced: set[str] = set()

    @property
    def source(self) -> str:
        """Name of the environment variable currently in use."""
        return self._candidates[self._index][0]

    def current(self) -> str:
        if self._index >= len(self._candidates):
            raise NoUsableKey("every configured Gemini key was rejected")
        name, key = self._candidates[self._index]
        if name not in self._announced:
            log.info("using Gemini key from %s", name)
            self._announced.add(name)
        return key

    def retire_current(self, reason: str) -> bool:
        """Drop the current key and advance. Returns True if another key remains."""
        retired = self.source
        self._index += 1
        if self._index < len(self._candidates):
            log.warning(
                "key from %s rejected (%s); falling back to %s",
                retired, reason, self.source,
            )
            return True
        log.error("key from %s rejected (%s); no keys remain", retired, reason)
        return False

    @property
    def exhausted(self) -> bool:
        return self._index >= len(self._candidates)
