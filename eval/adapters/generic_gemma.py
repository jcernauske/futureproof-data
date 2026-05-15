"""Generic Gemma adapter.

Used by golden cases that carry their own full {system, user, ...} payload —
which is most of them. The point of the adapter is to exercise the real
production gemma_client.py call path (caching, retry, JSONL logging, etc.)
without re-implementing prompt construction in the eval layer. The golden
case is responsible for matching the production prompt verbatim; any drift
is caught by `eval/tests/test_prompt_parity.py` (TODO — see eval/README.md).
"""

from __future__ import annotations

from typing import Any

from app.services import gemma_client

from eval.adapters.base import AdapterResult, time_call


class GenericGemmaAdapter:
    """Adapter that replays an arbitrary system/user prompt through
    gemma_client.generate. Suitable for any single-shot surface that does
    not use function calling.

    Golden case inputs MUST include:
      - system: str
      - user: str

    Optional inputs (forwarded if present):
      - max_tokens, temperature, seed, response_format, model, timeout_s

    The adapter stamps extra["call_site"] = <surface_name> so the latency
    log can be filtered correctly.
    """

    def __init__(self, surface_name: str, call_site: str, tier: str = "P0") -> None:
        self.surface_name = surface_name
        self._call_site = call_site
        self.tier = tier

    def run(self, inputs: dict[str, Any]) -> AdapterResult:
        try:
            system = inputs["system"]
            user = inputs["user"]
        except KeyError as exc:
            return AdapterResult(
                actual_output=None,
                latency_ms=0,
                error=f"missing_input: {exc}",
            )

        kwargs: dict[str, Any] = {
            "system": system,
            "user": user,
            "extra": {"call_site": self._call_site, "eval": True},
        }
        for opt in ("max_tokens", "temperature", "seed", "response_format", "model", "timeout_s"):
            if opt in inputs:
                kwargs[opt] = inputs[opt]

        try:
            text, latency_ms = time_call(gemma_client.generate, **kwargs)
        except Exception as exc:
            return AdapterResult(
                actual_output=None,
                latency_ms=0,
                error=f"adapter_exception: {type(exc).__name__}: {exc}",
            )

        actual: Any = text
        raw: dict[str, Any] = {"text": text}

        if inputs.get("response_format") in ("json", {"type": "json_object"}):
            import json
            try:
                actual = json.loads(text) if text else None
            except json.JSONDecodeError as exc:
                return AdapterResult(
                    actual_output=None,
                    latency_ms=latency_ms,
                    error=f"json_parse_error: {exc}",
                    raw=raw,
                )

        return AdapterResult(
            actual_output=actual,
            latency_ms=latency_ms,
            raw=raw,
        )
