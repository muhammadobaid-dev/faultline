"""The provider seam.

Everything that talks to a language model goes through `LLMProvider`. Gemini is the
only implementation we ship, but Gemini, DeepSeek and Perplexity all speak the
OpenAI-compatible format, so adding one later is a base-URL swap rather than a
rewrite. Nothing above this layer may import a vendor SDK or know a vendor's wire
format.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field


class Outcome(str, Enum):
    """How a provider call ended.

    Only `OK` can ever contribute to a grade. Every other outcome means we failed to
    obtain a response, which is our problem and never evidence that the target under
    test broke a rule. Confusing the two would produce false, defamatory grades.
    """

    OK = "ok"
    SAFETY_BLOCKED = "safety_blocked"  # the provider refused; neither pass nor fail
    RATE_LIMITED = "rate_limited"  # 429 against the per-minute ceiling; transient
    DEFERRED = "deferred"  # 429 against the daily cap; resumes at midnight Pacific
    UNAVAILABLE = "unavailable"  # 503; the model is briefly overloaded, retryable
    ERRORED = "errored"  # anything else, including retries exhausted

    @property
    def is_retryable(self) -> bool:
        return self in (Outcome.RATE_LIMITED, Outcome.UNAVAILABLE)


class Message(BaseModel):
    """One turn of a conversation with a target."""

    role: Literal["user", "model"]
    text: str


class LLMRequest(BaseModel):
    """A provider-agnostic request.

    `model` is always an explicit pinned version. Never a `-latest` alias: an alias
    rolling to a new model would change grades without the target changing, which
    would break the comparability guarantee that pinned test sets exist to protect.
    """

    model: str
    messages: list[Message]
    system_instruction: str | None = None
    temperature: float = 1.0
    max_output_tokens: int = 2048
    # A JSON Schema. When set, the provider must return JSON matching it.
    response_schema: dict[str, Any] | None = None
    # Relax the four configurable harm categories. Scoped deliberately: we set this
    # only where adversarial content genuinely requires it, never blanket-on.
    disable_safety_filters: bool = False

    def fingerprint(self) -> str:
        """Stable identity of this request, for cassette lookup."""
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()[:32]


class LLMResponse(BaseModel):
    """A provider-agnostic response. Never raises; failures are values."""

    outcome: Outcome
    text: str | None = None
    finish_reason: str | None = None
    block_reason: str | None = None
    http_status: int | None = None
    # Human-readable context for a non-OK outcome. Logged, never shown to a user.
    detail: str | None = None
    safety_ratings: list[dict[str, Any]] = Field(default_factory=list)

    # Which link in the fallback chain actually answered. Recorded on every result
    # so a verdict stays auditable and the single-family disclosure stays honest -
    # once the chain can reach DeepSeek, "graded by Gemini" is no longer a given.
    served_by: str | None = None
    served_by_model: str | None = None
    paid: bool = False

    @property
    def ok(self) -> bool:
        return self.outcome is Outcome.OK and bool(self.text)


class LLMProvider(Protocol):
    """The seam. One method, deliberately."""

    def generate(self, request: LLMRequest) -> LLMResponse: ...
