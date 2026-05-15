"""Career intent adapter — wraps the production _call_gemma_intent.

The intent surface lives at `intent._call_gemma_intent`. We call it directly
(private function — acceptable for an internal eval harness) so the eval
exercises the real production prompt template and parsing path. The golden
case provides the same inputs the prod code computes from school + DB.
"""

from __future__ import annotations

from typing import Any

from app.services.intent import _call_gemma_intent

from eval.adapters.base import AdapterResult, time_call


class CareerIntentAdapter:
    surface_name = "career_intent"
    tier = "P0"

    def run(self, inputs: dict[str, Any]) -> AdapterResult:
        required = {"student_input", "school_name", "school_cips", "crosswalk_cips"}
        missing = required - inputs.keys()
        if missing:
            return AdapterResult(
                actual_output=None,
                latency_ms=0,
                error=f"missing_inputs: {sorted(missing)}",
            )

        try:
            (parsed, latency_s, stats), wrapper_latency_ms = time_call(
                _call_gemma_intent,
                student_input=inputs["student_input"],
                school_name=inputs["school_name"],
                school_cips=inputs["school_cips"],
                crosswalk_cips=inputs["crosswalk_cips"],
                clarification=inputs.get("clarification"),
            )
        except Exception as exc:
            return AdapterResult(
                actual_output=None,
                latency_ms=0,
                error=f"adapter_exception: {type(exc).__name__}: {exc}",
            )

        return AdapterResult(
            actual_output=parsed,
            latency_ms=int(latency_s * 1000) if latency_s else wrapper_latency_ms,
            error=stats.get("parse_error"),
            raw=stats,
        )
