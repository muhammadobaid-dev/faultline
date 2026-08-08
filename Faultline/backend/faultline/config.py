"""Configuration. Secrets come from the environment, never from the repository."""

from __future__ import annotations

import os
from pathlib import Path

from faultline.providers.base import LLMProvider
from faultline.providers.budget import DailyBudget, ModelLimits
from faultline.providers.chain import ChainStep, FallbackChain
from faultline.providers.deepseek import DeepSeekProvider
from faultline.providers.gemini import GeminiProvider
from faultline.providers.keyring import KeyRing

BACKEND_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = BACKEND_ROOT / "fixtures"
CASSETTE_DIR = FIXTURES_DIR / "cassettes"
OUT_DIR = BACKEND_ROOT / "out"
LEDGER_PATH = OUT_DIR / "budget.json"

# Explicit pinned model versions. Never a `-latest` alias: an alias rolling to a new
# model would change grades without the target changing. The model id is part of a
# test set's identity.
TARGET_MODEL = "gemini-3.5-flash-lite"

# Measured, not assumed. On ten hand-authored borderline transcripts, Flash-Lite
# flagged 1 and confidently passed 6; Flash flagged 5 and confidently passed 1, with
# reasoning that quotes its evidence.
JUDGE_FIRST_PASS_MODEL = "gemini-3.6-flash"
JUDGE_ESCALATION_MODEL = "gemini-3.6-flash"
GENERATION_MODEL = "gemini-3.6-flash"

# Two keys on two separate Google accounts, so these are genuinely independent
# allowances rather than two straws in one cup.
GEMINI_ACCOUNTS = ("FAULTLINE_GEMINI_KEY_1", "FAULTLINE_GEMINI_KEY_2")
DEEPSEEK_ACCOUNT = "FAULTLINE_DEEPSEEK_KEY"
DEEPSEEK_MODEL = "deepseek-chat"

# Free-tier ceilings, per project and per model. `gemini-3.6-flash` is set from
# what we measured rather than what is published: it stopped answering after about
# thirty calls, far below the documented Flash-class allowance.
MODEL_LIMITS: dict[str, ModelLimits] = {
    "gemini-3.6-flash": ModelLimits(requests_per_minute=10, requests_per_day=25),
    "gemini-3.5-flash": ModelLimits(requests_per_minute=10, requests_per_day=250),
    "gemini-2.5-flash": ModelLimits(requests_per_minute=10, requests_per_day=250),
    "gemini-3.5-flash-lite": ModelLimits(requests_per_minute=15, requests_per_day=1000),
    # DeepSeek is deliberately absent: it has no hard daily wall, only cost.
}

# Anonymous Punchbag traffic draws from a reserved slice of the FREE allowance only,
# so strangers can never push the project onto paid DeepSeek. When this is spent the
# punchbag degrades to a labelled replay of a real run - never a faked live one.
PUNCHBAG_DAILY_REQUESTS = 150
PUNCHBAG_ACCOUNT = "punchbag"

# Quality tiers, best first. Within a tier both accounts are tried before dropping a
# tier, because a same-quality retry on a second free allowance beats a downgrade.
_GEMINI_TIERS = (
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-3.5-flash-lite",
)


class MissingAPIKey(RuntimeError):
    pass


def _gemini_steps(tiers: tuple[str, ...]) -> list[ChainStep]:
    return [
        ChainStep(provider="gemini", model=model, account=account)
        for model in tiers
        for account in GEMINI_ACCOUNTS
    ]


def judge_chain_steps() -> list[ChainStep]:
    return _gemini_steps(_GEMINI_TIERS) + [
        ChainStep(
            provider="deepseek", model=DEEPSEEK_MODEL,
            account=DEEPSEEK_ACCOUNT, paid=True,
        )
    ]


def attacker_chain_steps() -> list[ChainStep]:
    return _gemini_steps(_GEMINI_TIERS) + [
        ChainStep(
            provider="deepseek", model=DEEPSEEK_MODEL,
            account=DEEPSEEK_ACCOUNT, paid=True,
        )
    ]


def target_step(model: str = TARGET_MODEL) -> list[ChainStep]:
    """Deliberately one rung.

    The model under test is part of the test set's identity. Failing the target over
    to a different model would silently change what is being measured, so a quota
    failure here is `deferred` rather than a substitution.
    """
    return [ChainStep(provider="gemini", model=model, account=GEMINI_ACCOUNTS[0])]


def available_providers() -> dict[str, LLMProvider]:
    """One client per credential, keyed by account.

    Keyed by account rather than by vendor because each key carries its own
    independent allowance, and the chain needs to choose between them explicitly.
    """
    providers: dict[str, LLMProvider] = {}

    for name in GEMINI_ACCOUNTS:
        key = os.environ.get(name, "").strip()
        if key:
            providers[name] = GeminiProvider(KeyRing([(name, key)]))

    deepseek = os.environ.get(DEEPSEEK_ACCOUNT, "").strip()
    if deepseek:
        providers[DEEPSEEK_ACCOUNT] = DeepSeekProvider(deepseek)

    if not providers:
        raise MissingAPIKey(
            "No provider credentials found. Set at least one of: "
            + ", ".join([*GEMINI_ACCOUNTS, DEEPSEEK_ACCOUNT])
        )
    return providers


def budget() -> DailyBudget:
    return DailyBudget(path=LEDGER_PATH, limits=MODEL_LIMITS)


def allow_paid() -> bool:
    """Paid providers stay off unless switched on explicitly.

    Automatic fallback to a paid provider is silent spend by construction, so it is
    opt-in rather than default.
    """
    return os.environ.get("FAULTLINE_ALLOW_PAID", "").strip() in {"1", "true", "yes"}


def build_chain(
    steps: list[ChainStep], *, anonymous: bool = False, **kwargs
) -> FallbackChain:
    return FallbackChain(
        steps,
        available_providers(),
        budget(),
        allow_paid=allow_paid(),
        anonymous=anonymous,
        **kwargs,
    )
