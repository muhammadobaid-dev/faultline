"""The chain decides where money gets spent and what a verdict is attributed to,
so its rules are tested rather than trusted."""

from datetime import datetime, timedelta, timezone

import pytest

from faultline.providers.base import LLMRequest, LLMResponse, Message, Outcome
from faultline.providers.budget import DailyBudget, ModelLimits, pacific_day
from faultline.providers.chain import ChainStep, FallbackChain, NoProviderAvailable

LIMITS = {
    "good": ModelLimits(requests_per_minute=10, requests_per_day=2),
    "weak": ModelLimits(requests_per_minute=15, requests_per_day=50),
}


class Stub:
    def __init__(self, *responses: LLMResponse) -> None:
        self.queue = list(responses)
        self.seen: list[str] = []
        self.request_count = 0

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.request_count += 1
        self.seen.append(request.model)
        return self.queue.pop(0) if self.queue else OK


OK = LLMResponse(outcome=Outcome.OK, text="answered")
QUOTA = LLMResponse(outcome=Outcome.DEFERRED, http_status=429, detail="PerDay")
BOOM = LLMResponse(outcome=Outcome.UNAVAILABLE, http_status=503)


def a_request():
    return LLMRequest(model="ignored", messages=[Message(role="user", text="hi")])


def budget(tmp_path) -> DailyBudget:
    return DailyBudget(path=tmp_path / "ledger.json", limits=LIMITS)


FREE_1 = ChainStep(provider="gemini", model="good", account="KEY_1")
FREE_2 = ChainStep(provider="gemini", model="good", account="KEY_2")
WEAK_1 = ChainStep(provider="gemini", model="weak", account="KEY_1")
PAID = ChainStep(provider="deepseek", model="ds", account="PAID", paid=True)


def chain(tmp_path, steps, providers, **kw) -> FallbackChain:
    return FallbackChain(
        steps, providers, budget(tmp_path), sleep=lambda _: None, **kw
    )


# -- ordering ---------------------------------------------------------------


def test_the_first_healthy_rung_answers_and_is_recorded():
    pass  # covered by the next test; kept separate for readability of failures


def test_a_result_records_which_rung_produced_it(tmp_path):
    c = chain(tmp_path, [FREE_1, FREE_2], {"KEY_1": Stub(OK), "KEY_2": Stub()})
    result = c.generate(a_request())
    assert result.served_by == "gemini:good@KEY_1"
    assert result.served_by_model == "good"
    assert result.paid is False


def test_quota_on_one_account_falls_through_to_the_other(tmp_path):
    k1, k2 = Stub(QUOTA), Stub(OK)
    c = chain(tmp_path, [FREE_1, FREE_2], {"KEY_1": k1, "KEY_2": k2})
    result = c.generate(a_request())
    assert result.ok
    assert result.served_by == "gemini:good@KEY_2"


def test_a_per_day_quota_error_marks_that_pairing_spent(tmp_path):
    ledger = budget(tmp_path)
    c = FallbackChain(
        [FREE_1, FREE_2], {"KEY_1": Stub(QUOTA), "KEY_2": Stub(OK)}, ledger,
        sleep=lambda _: None,
    )
    c.generate(a_request())
    # The provider's own word beats our counter: retrying today cannot help.
    assert not ledger.has_room("KEY_1", "good")
    assert ledger.has_room("KEY_2", "good")


def test_a_downgrade_happens_only_after_both_accounts_are_spent(tmp_path):
    k1, k2 = Stub(QUOTA, OK), Stub(QUOTA)
    c = chain(tmp_path, [FREE_1, FREE_2, WEAK_1], {"KEY_1": k1, "KEY_2": k2})
    result = c.generate(a_request())
    assert result.ok
    assert result.served_by == "gemini:weak@KEY_1"
    assert k1.seen == ["good", "weak"], "must exhaust the better model first"


def test_a_transient_failure_is_retried_before_moving_on(tmp_path):
    k1 = Stub(BOOM, BOOM, OK)
    c = chain(tmp_path, [FREE_1, FREE_2], {"KEY_1": k1, "KEY_2": Stub()},
              max_attempts_per_step=3)
    assert c.generate(a_request()).served_by == "gemini:good@KEY_1"
    assert k1.request_count == 3


# -- the money rules --------------------------------------------------------


def test_anonymous_traffic_can_never_reach_a_paid_provider(tmp_path):
    # Punchbag Mode is public and unauthenticated. A chain that reaches a paid
    # provider means strangers spend real money.
    paid = Stub(OK)
    c = chain(
        tmp_path, [FREE_1, PAID], {"KEY_1": Stub(QUOTA), "PAID": paid},
        allow_paid=True, anonymous=True,
    )
    result = c.generate(a_request())
    assert paid.request_count == 0
    assert not result.ok


def test_paid_providers_are_off_unless_explicitly_enabled(tmp_path):
    paid = Stub(OK)
    c = chain(tmp_path, [FREE_1, PAID], {"KEY_1": Stub(QUOTA), "PAID": paid})
    c.generate(a_request())
    assert paid.request_count == 0


def test_paid_providers_are_reached_when_enabled_and_authenticated(tmp_path):
    paid = Stub(LLMResponse(outcome=Outcome.OK, text="answered", paid=True))
    c = chain(tmp_path, [FREE_1, PAID], {"KEY_1": Stub(QUOTA), "PAID": paid},
              allow_paid=True)
    result = c.generate(a_request())
    assert result.ok
    assert result.paid is True
    assert result.served_by == "deepseek:ds@PAID"


def test_an_unconfigured_credential_is_skipped_not_fatal(tmp_path):
    c = chain(tmp_path, [FREE_1, FREE_2], {"KEY_2": Stub(OK)})
    assert c.generate(a_request()).served_by == "gemini:good@KEY_2"


def test_a_chain_with_nothing_usable_raises_rather_than_returning_a_pass(tmp_path):
    c = chain(tmp_path, [FREE_1, PAID], {})
    with pytest.raises(NoProviderAvailable):
        c.generate(a_request())


# -- the ledger -------------------------------------------------------------


def test_the_ledger_counts_per_account_and_per_model(tmp_path):
    ledger = budget(tmp_path)
    ledger.record("KEY_1", "good")
    assert ledger.spent("KEY_1", "good") == 1
    assert ledger.spent("KEY_2", "good") == 0, "accounts are independent allowances"
    assert ledger.spent("KEY_1", "weak") == 0, "models are independent allowances"


def test_the_ledger_survives_a_restart(tmp_path):
    # A run can outlive a process; the Render service spins down when idle.
    first = budget(tmp_path)
    first.record("KEY_1", "good")
    assert budget(tmp_path).spent("KEY_1", "good") == 1


def test_an_unmetered_model_always_has_room(tmp_path):
    # DeepSeek has no daily wall, only cost.
    assert budget(tmp_path).has_room("PAID", "ds")


def test_the_daily_bucket_is_a_pacific_date():
    utc_morning = datetime(2026, 7, 25, 3, 0, tzinfo=timezone.utc)
    # 03:00 UTC is still the previous evening in California.
    assert pacific_day(utc_morning) == "2026-07-24"
    assert pacific_day(utc_morning + timedelta(hours=12)) == "2026-07-25"


def test_a_spent_allowance_is_skipped_without_a_call(tmp_path):
    ledger = budget(tmp_path)
    ledger.exhaust("KEY_1", "good")
    k1 = Stub(OK)
    c = FallbackChain([FREE_1, FREE_2], {"KEY_1": k1, "KEY_2": Stub(OK)}, ledger,
                      sleep=lambda _: None)
    result = c.generate(a_request())
    assert k1.request_count == 0, "a spent allowance must not be probed"
    assert result.served_by == "gemini:good@KEY_2"
