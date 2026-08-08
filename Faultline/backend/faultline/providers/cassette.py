"""Record and replay, wrapped around any provider.

Our whole AI layer runs on a shared 1,500-requests-per-day allowance. Iterating on a
judge prompt means running the same cases dozens of times, which would burn that
allowance on work we have already paid for once. A cassette records each real
response to disk and replays it thereafter, so development and tests cost nothing and
are deterministic.

It also makes the golden set cheap: target responses become static fixtures, leaving
only the judge call to spend quota.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from faultline.providers.base import LLMProvider, LLMRequest, LLMResponse, Outcome


class CassetteMode(str, Enum):
    AUTO = "auto"  # replay when we have it, otherwise call through and record
    REPLAY = "replay"  # never call through; a miss is an error
    RECORD = "record"  # always call through and overwrite
    BYPASS = "bypass"  # ignore the cassette entirely


class CassetteMiss(RuntimeError):
    """Replay was required but nothing was recorded for this request."""


class CassetteProvider(LLMProvider):
    def __init__(
        self,
        inner: LLMProvider,
        directory: Path,
        mode: CassetteMode = CassetteMode.AUTO,
    ) -> None:
        self._inner = inner
        self._dir = Path(directory)
        self._mode = mode
        self.replayed = 0
        self.recorded = 0

    def generate(self, request: LLMRequest) -> LLMResponse:
        if self._mode is CassetteMode.BYPASS:
            return self._inner.generate(request)

        path = self._path_for(request)

        if self._mode in (CassetteMode.AUTO, CassetteMode.REPLAY) and path.exists():
            self.replayed += 1
            return LLMResponse.model_validate_json(
                path.read_text(encoding="utf-8")
            )

        if self._mode is CassetteMode.REPLAY:
            raise CassetteMiss(
                f"no recording for {request.model} request {request.fingerprint()}"
            )

        response = self._inner.generate(request)

        # Only record successes and safety blocks. A 429 or 503 is a fact about the
        # moment, not about the request, and replaying one forever would be a lie.
        if response.outcome in (Outcome.OK, Outcome.SAFETY_BLOCKED):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(response.model_dump_json(indent=2), encoding="utf-8")
            self._write_sidecar(path, request)
            self.recorded += 1

        return response

    def _path_for(self, request: LLMRequest) -> Path:
        return self._dir / request.model / f"{request.fingerprint()}.json"

    def _write_sidecar(self, path: Path, request: LLMRequest) -> None:
        """Store the request beside the response so recordings stay auditable."""
        sidecar = path.with_suffix(".request.json")
        sidecar.write_text(
            json.dumps(request.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )
