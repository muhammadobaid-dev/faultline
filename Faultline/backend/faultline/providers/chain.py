"""The fallback chain.

One ordered list of (provider, model, credential) steps. A call walks the list until
something answers, so a run degrades through quality tiers instead of dying at the
first quota wall.

Order matters in a way that is easy to get wrong. Gemini's free quota is metered per
model as well as per project, so the cheapest fallback is a *different Gemini model
on the same key* - free and instant. Switching keys comes next, since our two keys sit
on separate Google accounts and are genuinely independent allowances. Only when every
free tier is spent does the chain reach a paid provider.

Two safety properties are enforced here rather than left to discipline:
  - anonymous traffic can never reach a paid provider, flag or no flag;
  - the target under test never fails over at all, because swapping the model
    mid-run would silently change what is being measured.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from faultline.providers.base import LLMProvider, LLMRequest, LLMResponse, Outcome
from faultline.providers.budget import DailyBudget

log = logging.getLogger("faultline.chain")


@dataclass(frozen=True)
class ChainStep:
    """One rung: which provider, which model, on whose allowance."""

    provider: str  # "gemini" | "deepseek"
    model: str
    account: str  # env var name, used as the ledger's account identity
    paid: bool = False

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.model}@{self.account}"


class NoProviderAvailable(RuntimeError):
    """Every rung was skipped or refused, and nothing answered."""


class FallbackChain(LLMProvider):
    def __init__(
        self,
        steps: list[ChainStep],
        providers: dict[str, LLMProvider],
        budget: DailyBudget,
        *,
        allow_paid: bool = False,
        anonymous: bool = False,
        max_attempts_per_step: int = 3,
        backoff_seconds: float = 2.0,
        sleep=time.sleep,
    ) -> None:
        self._steps = steps
        self._providers = providers
        self._budget = budget
        self._allow_paid = allow_paid
        self._anonymous = anonymous
        self._max_attempts = max_attempts_per_step
        self._backoff = backoff_seconds
        self._sleep = sleep
        self.failovers: list[tuple[str, str]] = []  # (step label, reason)

    def usable(self, step: ChainStep) -> tuple[bool, str]:
        """Whether this rung may be attempted at all, and why not if it may not."""
        if step.paid:
            if self._anonymous:
                # Hard rule. Punchbag Mode is public and unauthenticated; a chain
                # that reaches a paid provider means strangers spend real money.
                return False, "paid providers are unreachable from anonymous traffic"
            if not self._allow_paid:
                return False, "paid providers are disabled"
        if step.account not in self._providers:
            return False, "no credential configured"
        if not self._budget.has_room(step.account, step.model):
            return False, "daily allowance spent"
        return True, ""

    def generate(self, request: LLMRequest) -> LLMResponse:
        last: LLMResponse | None = None

        for step in self._steps:
            ok, why = self.usable(step)
            if not ok:
                log.info("skipping %s: %s", step.label, why)
                self.failovers.append((step.label, why))
                continue

            response = self._attempt(step, request)
            if response.ok:
                response.served_by = step.label
                response.served_by_model = step.model
                response.paid = step.paid
                return response

            last = response
            reason = response.detail or response.outcome.value
            log.warning("%s did not answer (%s); moving down the chain",
                        step.label, response.outcome.value)
            self.failovers.append((step.label, response.outcome.value))

            if response.outcome is Outcome.DEFERRED:
                # The provider's own word that this pairing is done for the day.
                self._budget.exhaust(step.account, step.model)
            _ = reason

        if last is not None:
            last.served_by = None
            return last
        raise NoProviderAvailable(
            "no usable provider: " + "; ".join(f"{s}={r}" for s, r in self.failovers)
        )

    def _attempt(self, step: ChainStep, request: LLMRequest) -> LLMResponse:
        """One rung, with backoff on the failures that are worth retrying."""
        # Keyed by account, not by vendor: each credential is its own client with
        # its own independent allowance.
        provider = self._providers[step.account]
        attempt_request = request.model_copy(update={"model": step.model})
        response = LLMResponse(outcome=Outcome.ERRORED, detail="not attempted")

        for attempt in range(self._max_attempts):
            self._budget.record(step.account, step.model)
            response = provider.generate(attempt_request)
            if response.ok or not response.outcome.is_retryable:
                return response
            if attempt < self._max_attempts - 1:
                delay = self._backoff * (2**attempt)
                log.info("%s returned %s; retrying in %.1fs",
                         step.label, response.outcome.value, delay)
                self._sleep(delay)
        return response
