"""The key ring exists because a dead key is invisible to every cheap check.

Both ListModels and countTokens returned 200 on a Google Cloud project that could not
generate at all, so failover has to happen on the real call.
"""

import io
import urllib.error
from unittest.mock import patch

import pytest

from faultline.providers.base import LLMRequest, Message, Outcome
from faultline.providers.gemini import GeminiProvider
from faultline.providers.keyring import KeyRing, NoUsableKey

DENIED = '{"error":{"code":403,"message":"Your project has been denied access.",' \
         '"status":"PERMISSION_DENIED"}}'


def a_request():
    return LLMRequest(model="m", messages=[Message(role="user", text="hi")])


def http_error(code: int, body: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="https://example.test", code=code, msg="e", hdrs=None, fp=io.BytesIO(body.encode())
    )


def test_empty_candidates_are_skipped():
    ring = KeyRing([("EMPTY", ""), ("REAL", "abc")])
    assert ring.source == "REAL"


def test_a_ring_with_no_keys_at_all_is_an_error():
    with pytest.raises(NoUsableKey):
        KeyRing([("EMPTY", ""), ("ALSO_EMPTY", "")])


def test_retiring_advances_to_the_next_key():
    ring = KeyRing([("DEV", "dead"), ("PROD", "live")])
    assert ring.source == "DEV"
    assert ring.retire_current("denied") is True
    assert ring.source == "PROD"
    assert ring.retire_current("denied") is False
    assert ring.exhausted


def test_a_denied_project_fails_over_to_the_next_key_transparently():
    ring = KeyRing([("DEV", "dead-key"), ("PROD", "live-key")])
    provider = GeminiProvider(ring)
    used: list[str] = []

    def fake_post(model, body):
        used.append(ring.current())
        if ring.current() == "dead-key":
            raise http_error(403, DENIED)
        return {"candidates": [{"finishReason": "STOP",
                                "content": {"parts": [{"text": "ok"}]}}]}

    with patch.object(GeminiProvider, "_post", side_effect=fake_post):
        result = provider.generate(a_request())

    assert result.outcome is Outcome.OK
    assert used == ["dead-key", "live-key"]
    assert ring.source == "PROD"


def test_the_dead_key_is_only_tried_once_across_calls():
    ring = KeyRing([("DEV", "dead-key"), ("PROD", "live-key")])
    provider = GeminiProvider(ring)
    attempts: list[str] = []

    def fake_post(model, body):
        attempts.append(ring.current())
        if ring.current() == "dead-key":
            raise http_error(403, DENIED)
        return {"candidates": [{"finishReason": "STOP",
                                "content": {"parts": [{"text": "ok"}]}}]}

    with patch.object(GeminiProvider, "_post", side_effect=fake_post):
        provider.generate(a_request())
        provider.generate(a_request())

    assert attempts.count("dead-key") == 1, "a retired key must not be retried"


def test_a_non_403_failure_does_not_burn_a_key():
    ring = KeyRing([("DEV", "k1"), ("PROD", "k2")])
    provider = GeminiProvider(ring)

    with patch.object(GeminiProvider, "_post", side_effect=http_error(503, "{}")):
        result = provider.generate(a_request())

    assert result.outcome is Outcome.UNAVAILABLE
    assert ring.source == "DEV", "a transient error must not retire the key"


def test_exhausting_every_key_returns_the_last_failure():
    ring = KeyRing([("DEV", "k1"), ("PROD", "k2")])
    provider = GeminiProvider(ring)

    # A fresh error per call: an HTTPError's body is a stream and can only be read once.
    def always_denied(model, body):
        raise http_error(403, DENIED)

    with patch.object(GeminiProvider, "_post", side_effect=always_denied):
        result = provider.generate(a_request())

    assert result.outcome is Outcome.ERRORED
    assert ring.exhausted
