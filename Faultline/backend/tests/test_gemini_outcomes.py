"""The outcome classifier is load-bearing: it decides whether a provider hiccup gets
mistaken for a target failure. Every branch is tested against real response shapes."""

import io
import urllib.error

import pytest

from faultline.providers.base import LLMRequest, Message, Outcome
from faultline.providers.gemini import GeminiProvider
from faultline.providers.keyring import KeyRing

provider = GeminiProvider(KeyRing([("TEST_VAR", "test-key-not-used")]))


def http_error(code: int, body: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="https://example.test", code=code, msg="err", hdrs=None,
        fp=io.BytesIO(body.encode()),
    )


def test_a_normal_response_is_ok():
    result = provider._from_wire(
        {"candidates": [{"finishReason": "STOP",
                         "content": {"parts": [{"text": "hello"}]}}]}
    )
    assert result.outcome is Outcome.OK
    assert result.text == "hello"
    assert result.ok


def test_a_blocked_prompt_is_safety_blocked_not_a_failure():
    result = provider._from_wire({"promptFeedback": {"blockReason": "SAFETY"}})
    assert result.outcome is Outcome.SAFETY_BLOCKED
    assert result.block_reason == "SAFETY"
    assert not result.ok


def test_a_blocked_candidate_is_safety_blocked():
    result = provider._from_wire({"candidates": [{"finishReason": "SAFETY"}]})
    assert result.outcome is Outcome.SAFETY_BLOCKED


def test_an_empty_candidate_is_an_error_not_an_empty_pass():
    # An empty string must never be graded as "the target said nothing wrong".
    result = provider._from_wire({"candidates": [{"finishReason": "MAX_TOKENS"}]})
    assert result.outcome is Outcome.ERRORED


def test_no_candidates_is_an_error():
    assert provider._from_wire({"candidates": []}).outcome is Outcome.ERRORED


def test_a_per_minute_429_is_transient():
    result = provider._from_http_error(
        http_error(429, '{"error":{"message":"Quota exceeded for '
                        'GenerateRequestsPerMinutePerProject"}}')
    )
    assert result.outcome is Outcome.RATE_LIMITED
    assert result.outcome.is_retryable


def test_a_per_day_429_is_deferred_until_the_reset():
    # Retrying this in ten seconds cannot help; it needs the midnight-Pacific reset.
    result = provider._from_http_error(
        http_error(429, '{"error":{"message":"Quota exceeded for '
                        'GenerateRequestsPerDayPerProjectPerModel"}}')
    )
    assert result.outcome is Outcome.DEFERRED
    assert not result.outcome.is_retryable


def test_a_503_is_transient_and_retryable():
    # Observed in the step-zero probe: one judge call in eighteen came back 503.
    result = provider._from_http_error(http_error(503, '{"error":{"code":503}}'))
    assert result.outcome is Outcome.UNAVAILABLE
    assert result.outcome.is_retryable


def test_a_403_is_an_error():
    result = provider._from_http_error(
        http_error(403, '{"error":{"message":"Your project has been denied access."}}')
    )
    assert result.outcome is Outcome.ERRORED
    assert "denied access" in result.detail


@pytest.mark.parametrize("outcome", list(Outcome))
def test_only_ok_can_carry_a_gradeable_response(outcome):
    from faultline.providers.base import LLMResponse

    response = LLMResponse(outcome=outcome, text="some text")
    assert response.ok is (outcome is Outcome.OK)


def test_safety_settings_are_only_sent_when_asked_for():
    off = provider._to_wire(
        LLMRequest(model="m", messages=[Message(role="user", text="hi")])
    )
    assert "safetySettings" not in off

    on = provider._to_wire(
        LLMRequest(model="m", messages=[Message(role="user", text="hi")],
                   disable_safety_filters=True)
    )
    assert len(on["safetySettings"]) == 4
    assert all(s["threshold"] == "BLOCK_NONE" for s in on["safetySettings"])


def test_a_response_schema_switches_the_request_to_json():
    wire = provider._to_wire(
        LLMRequest(model="m", messages=[Message(role="user", text="hi")],
                   response_schema={"type": "object"})
    )
    assert wire["generationConfig"]["responseMimeType"] == "application/json"


def test_the_same_request_fingerprints_stably():
    a = LLMRequest(model="m", messages=[Message(role="user", text="hi")])
    b = LLMRequest(model="m", messages=[Message(role="user", text="hi")])
    c = LLMRequest(model="m", messages=[Message(role="user", text="different")])
    assert a.fingerprint() == b.fingerprint()
    assert a.fingerprint() != c.fingerprint()
