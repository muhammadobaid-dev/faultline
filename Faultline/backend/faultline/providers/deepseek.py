"""DeepSeek, over its OpenAI-compatible endpoint.

The pressure-release valve at the end of both chains. DeepSeek publishes no hard
per-minute cap - under load it slows rather than rejecting, returning 429 only when
it must - so unlike Gemini it has no daily wall. Its only real limit is cost, which
is why every call through it is logged at WARNING rather than counted silently.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from faultline.providers.base import LLMProvider, LLMRequest, LLMResponse, Outcome

log = logging.getLogger("faultline.deepseek")

_ENDPOINT = "https://api.deepseek.com/chat/completions"


class DeepSeekProvider(LLMProvider):
    """Paid. Never reachable from anonymous traffic - see PaidGate in chain.py."""

    def __init__(self, api_key: str, *, timeout: int = 120) -> None:
        if not api_key:
            raise ValueError("DeepSeek API key is empty")
        self._api_key = api_key
        self._timeout = timeout
        self.request_count = 0

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.request_count += 1
        log.warning(
            "falling through to DeepSeek (paid) for model %s - this call costs money",
            request.model,
        )
        try:
            raw = self._post(self._to_wire(request))
        except urllib.error.HTTPError as e:
            return self._from_http_error(e)
        except Exception as e:
            return LLMResponse(outcome=Outcome.ERRORED, detail=repr(e), paid=True)
        return self._from_wire(raw)

    def _to_wire(self, request: LLMRequest) -> dict[str, Any]:
        messages: list[dict[str, str]] = []
        if request.system_instruction:
            messages.append({"role": "system", "content": request.system_instruction})
        for m in request.messages:
            # Gemini calls the model turn "model"; OpenAI-compatible calls it
            # "assistant". The seam exists so nothing above here has to know.
            messages.append(
                {
                    "role": "assistant" if m.role == "model" else "user",
                    "content": m.text,
                }
            )

        body: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
        }
        if request.response_schema is not None:
            # DeepSeek supports JSON mode but not a schema, so the schema is
            # restated in the prompt and validated by Pydantic on the way out.
            body["response_format"] = {"type": "json_object"}
        return body

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(
            _ENDPOINT,
            data=json.dumps(body).encode(),
            headers={
                "content-type": "application/json",
                "authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as r:
            return json.loads(r.read())

    def _from_http_error(self, e: urllib.error.HTTPError) -> LLMResponse:
        detail = ""
        try:
            detail = e.read().decode()[:1500]
        except Exception:
            pass
        if e.code == 429:
            outcome = Outcome.RATE_LIMITED  # load, not a daily wall
        elif e.code == 402:
            log.error("DeepSeek reports insufficient balance")
            outcome = Outcome.DEFERRED
        elif e.code >= 500:
            outcome = Outcome.UNAVAILABLE
        else:
            outcome = Outcome.ERRORED
        return LLMResponse(
            outcome=outcome, http_status=e.code, detail=detail, paid=True
        )

    def _from_wire(self, raw: dict[str, Any]) -> LLMResponse:
        choices = raw.get("choices") or []
        if not choices:
            return LLMResponse(
                outcome=Outcome.ERRORED, http_status=200,
                detail="no choices returned", paid=True,
            )
        choice = choices[0]
        text = (choice.get("message") or {}).get("content") or None
        finish = choice.get("finish_reason")
        if text is None:
            return LLMResponse(
                outcome=Outcome.ERRORED, http_status=200, finish_reason=finish,
                detail=f"empty choice (finish_reason={finish})", paid=True,
            )
        return LLMResponse(
            outcome=Outcome.OK, text=text, http_status=200,
            finish_reason=finish, paid=True,
        )
