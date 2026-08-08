"""Gemini implementation of the provider seam, over the REST API.

Uses the standard library only. The slice has no HTTP dependency; when the backend
phase arrives this is the one file that changes to `google-genai`, and nothing above
the seam notices.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from faultline.providers.base import LLMProvider, LLMRequest, LLMResponse, Outcome
from faultline.providers.keyring import KeyRing

_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# The four configurable harm categories. Core protections (child safety) are not
# adjustable and none of our packs go near them.
_CONFIGURABLE_HARM_CATEGORIES = (
    "HARM_CATEGORY_HARASSMENT",
    "HARM_CATEGORY_HATE_SPEECH",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "HARM_CATEGORY_DANGEROUS_CONTENT",
)


def _is_project_denied(status: int, detail: str) -> bool:
    """A 403 PERMISSION_DENIED means this key's project cannot generate at all.

    Distinct from any other failure: retrying with the same key can never help, but
    retrying with a different key very well might.
    """
    return status == 403 and "PERMISSION_DENIED" in detail


class GeminiProvider(LLMProvider):
    def __init__(self, keys: KeyRing, *, timeout: int = 90) -> None:
        self._keys = keys
        self._timeout = timeout
        self.request_count = 0

    @property
    def key_source(self) -> str:
        return self._keys.source

    def generate(self, request: LLMRequest) -> LLMResponse:
        wire = self._to_wire(request)
        while True:
            self.request_count += 1
            try:
                return self._from_wire(self._post(request.model, wire))
            except urllib.error.HTTPError as e:
                response = self._from_http_error(e)
            except Exception as e:  # network-level failure
                return LLMResponse(outcome=Outcome.ERRORED, detail=repr(e))

            # A denied project is a property of the key, not of the request. Retire
            # it and try the next one rather than failing the whole run.
            if _is_project_denied(response.http_status or 0, response.detail or ""):
                if self._keys.retire_current("project denied access"):
                    continue
            return response

    # -- wire format ------------------------------------------------------

    def _to_wire(self, request: LLMRequest) -> dict[str, Any]:
        generation_config: dict[str, Any] = {
            "temperature": request.temperature,
            "maxOutputTokens": request.max_output_tokens,
        }
        if request.response_schema is not None:
            generation_config["responseMimeType"] = "application/json"
            generation_config["responseSchema"] = request.response_schema

        body: dict[str, Any] = {
            "contents": [
                {"role": m.role, "parts": [{"text": m.text}]} for m in request.messages
            ],
            "generationConfig": generation_config,
        }
        if request.system_instruction:
            body["systemInstruction"] = {"parts": [{"text": request.system_instruction}]}
        if request.disable_safety_filters:
            body["safetySettings"] = [
                {"category": c, "threshold": "BLOCK_NONE"}
                for c in _CONFIGURABLE_HARM_CATEGORIES
            ]
        return body

    def _post(self, model: str, body: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(
            f"{_BASE}/{model}:generateContent",
            data=json.dumps(body).encode(),
            headers={
                "content-type": "application/json",
                "x-goog-api-key": self._keys.current(),
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as r:
            return json.loads(r.read())

    # -- outcome classification -------------------------------------------

    def _from_http_error(self, e: urllib.error.HTTPError) -> LLMResponse:
        detail = ""
        try:
            detail = e.read().decode()[:1500]
        except Exception:
            pass

        if e.code == 429:
            # Distinguish the per-minute ceiling from the daily cap: the first is
            # transient and worth retrying in seconds, the second cannot succeed
            # again until the midnight-Pacific reset.
            per_day = "PerDay" in detail or "per day" in detail.lower()
            outcome = Outcome.DEFERRED if per_day else Outcome.RATE_LIMITED
        elif e.code == 503:
            outcome = Outcome.UNAVAILABLE
        else:
            outcome = Outcome.ERRORED

        return LLMResponse(outcome=outcome, http_status=e.code, detail=detail)

    def _from_wire(self, raw: dict[str, Any]) -> LLMResponse:
        prompt_feedback = raw.get("promptFeedback") or {}
        block_reason = prompt_feedback.get("blockReason")
        if block_reason:
            # The prompt itself was refused; we never saw the target's behavior.
            return LLMResponse(
                outcome=Outcome.SAFETY_BLOCKED,
                http_status=200,
                block_reason=block_reason,
                safety_ratings=prompt_feedback.get("safetyRatings") or [],
                detail="prompt blocked before generation",
            )

        candidates = raw.get("candidates") or []
        if not candidates:
            return LLMResponse(
                outcome=Outcome.ERRORED,
                http_status=200,
                detail="no candidates returned",
            )

        candidate = candidates[0]
        finish_reason = candidate.get("finishReason")
        safety_ratings = candidate.get("safetyRatings") or []

        if finish_reason == "SAFETY":
            return LLMResponse(
                outcome=Outcome.SAFETY_BLOCKED,
                http_status=200,
                finish_reason=finish_reason,
                safety_ratings=safety_ratings,
                detail="candidate blocked after generation",
            )

        parts = (candidate.get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts) or None
        if text is None:
            return LLMResponse(
                outcome=Outcome.ERRORED,
                http_status=200,
                finish_reason=finish_reason,
                safety_ratings=safety_ratings,
                detail=f"empty candidate (finish_reason={finish_reason})",
            )

        return LLMResponse(
            outcome=Outcome.OK,
            text=text,
            http_status=200,
            finish_reason=finish_reason,
            safety_ratings=safety_ratings,
        )
