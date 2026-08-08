import pytest

from faultline.providers.base import LLMRequest, LLMResponse, Message, Outcome
from faultline.providers.cassette import CassetteMiss, CassetteMode, CassetteProvider


class CountingProvider:
    """A stand-in that records how often it was actually called."""

    def __init__(self, response: LLMResponse) -> None:
        self.response = response
        self.calls = 0

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        return self.response


def a_request(text: str = "hello") -> LLMRequest:
    return LLMRequest(model="test-model", messages=[Message(role="user", text=text)])


OK = LLMResponse(outcome=Outcome.OK, text="hi there", http_status=200)


def test_auto_mode_calls_through_once_then_replays(tmp_path):
    inner = CountingProvider(OK)
    cassette = CassetteProvider(inner, tmp_path, CassetteMode.AUTO)

    first = cassette.generate(a_request())
    second = cassette.generate(a_request())

    assert inner.calls == 1, "the second call should have been served from disk"
    assert first.text == second.text == "hi there"
    assert cassette.recorded == 1
    assert cassette.replayed == 1


def test_different_requests_get_different_recordings(tmp_path):
    inner = CountingProvider(OK)
    cassette = CassetteProvider(inner, tmp_path, CassetteMode.AUTO)

    cassette.generate(a_request("one"))
    cassette.generate(a_request("two"))

    assert inner.calls == 2


def test_replay_mode_never_calls_through(tmp_path):
    inner = CountingProvider(OK)
    CassetteProvider(inner, tmp_path, CassetteMode.AUTO).generate(a_request())
    assert inner.calls == 1

    strict = CassetteProvider(inner, tmp_path, CassetteMode.REPLAY)
    assert strict.generate(a_request()).text == "hi there"
    assert inner.calls == 1


def test_replay_mode_raises_on_a_miss(tmp_path):
    strict = CassetteProvider(CountingProvider(OK), tmp_path, CassetteMode.REPLAY)
    with pytest.raises(CassetteMiss):
        strict.generate(a_request("never recorded"))


@pytest.mark.parametrize(
    "outcome", [Outcome.RATE_LIMITED, Outcome.DEFERRED, Outcome.UNAVAILABLE, Outcome.ERRORED]
)
def test_transient_failures_are_not_recorded(tmp_path, outcome):
    # A 429 or 503 is a fact about the moment, not about the request. Recording one
    # would replay a failure forever and look like a permanent property of the case.
    inner = CountingProvider(LLMResponse(outcome=outcome, detail="transient"))
    cassette = CassetteProvider(inner, tmp_path, CassetteMode.AUTO)

    cassette.generate(a_request())
    cassette.generate(a_request())

    assert inner.calls == 2
    assert cassette.recorded == 0


def test_safety_blocks_are_recorded(tmp_path):
    # A safety block is a stable property of the request, so it replays correctly.
    inner = CountingProvider(
        LLMResponse(outcome=Outcome.SAFETY_BLOCKED, block_reason="SAFETY")
    )
    cassette = CassetteProvider(inner, tmp_path, CassetteMode.AUTO)

    cassette.generate(a_request())
    replayed = cassette.generate(a_request())

    assert inner.calls == 1
    assert replayed.outcome is Outcome.SAFETY_BLOCKED
    assert replayed.block_reason == "SAFETY"


def test_bypass_mode_ignores_the_cassette(tmp_path):
    inner = CountingProvider(OK)
    cassette = CassetteProvider(inner, tmp_path, CassetteMode.BYPASS)
    cassette.generate(a_request())
    cassette.generate(a_request())
    assert inner.calls == 2


def test_a_recording_leaves_an_auditable_request_beside_it(tmp_path):
    cassette = CassetteProvider(CountingProvider(OK), tmp_path, CassetteMode.AUTO)
    cassette.generate(a_request())
    assert list(tmp_path.rglob("*.request.json")), "no sidecar written"
