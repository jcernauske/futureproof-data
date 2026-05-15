"""Adapter registry. Maps surface name → adapter instance.

Most surfaces use the GenericGemmaAdapter probe; only a few have authentic
wrappers around real prod functions (e.g., career_intent). To add an
adapter, register it here and reference it from a golden case file.
"""

from __future__ import annotations

from eval.adapters.base import SurfaceAdapter
from eval.adapters.career_intent import CareerIntentAdapter
from eval.adapters.generic_gemma import GenericGemmaAdapter


def _build_registry() -> dict[str, SurfaceAdapter]:
    return {
        # --- P0 authentic ---
        "career_intent": CareerIntentAdapter(),
        # --- P0 generic probes (carry full prompt in golden case) ---
        "explain_ern": GenericGemmaAdapter("explain_ern", "explain_ern_receipt", tier="P0"),
        "explain_roi": GenericGemmaAdapter("explain_roi", "explain_roi_receipt", tier="P0"),
        "explain_res": GenericGemmaAdapter("explain_res", "explain_res_receipt", tier="P0"),
        "explain_grw": GenericGemmaAdapter("explain_grw", "explain_grw_receipt", tier="P0"),
        "explain_aura": GenericGemmaAdapter("explain_aura", "explain_aura_receipt", tier="P0"),
        # --- P1 generic probes ---
        "boss_narrative": GenericGemmaAdapter("boss_narrative", "boss_narrative", tier="P1"),
        "career_description": GenericGemmaAdapter(
            "career_description", "career_description", tier="P1"
        ),
        "next_steps": GenericGemmaAdapter("next_steps", "next_steps", tier="P1"),
        "guidance": GenericGemmaAdapter("guidance", "guidance", tier="P1"),
        # --- P2 ---
        "skill_pool": GenericGemmaAdapter("skill_pool", "skill_pool", tier="P2"),
    }


_REGISTRY: dict[str, SurfaceAdapter] = _build_registry()


def get_adapter(surface: str) -> SurfaceAdapter:
    if surface not in _REGISTRY:
        raise KeyError(
            f"No adapter registered for surface {surface!r}. "
            f"Known: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[surface]


def known_surfaces() -> list[str]:
    return sorted(_REGISTRY)


def surfaces_in_tier(tier: str) -> list[str]:
    return sorted(s for s, a in _REGISTRY.items() if a.tier == tier)
