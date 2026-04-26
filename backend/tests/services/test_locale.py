"""Tests for the locale service — normalize, instruction, fallback.

Covers the three public functions in app.services.locale:
  - normalize_locale: type-coercion + fallback to "en"
  - gemma_language_instruction: Spanish vs English instruction blocks
  - fallback_text: per-key, per-locale degraded copy
"""

from __future__ import annotations

import pytest

from app.services.locale import (
    DEFAULT_LOCALE,
    fallback_text,
    gemma_language_instruction,
    normalize_locale,
)

# ---------------------------------------------------------------------------
# normalize_locale
# ---------------------------------------------------------------------------


class TestNormalizeLocale:
    def test_es_returns_es(self):
        assert normalize_locale("es") == "es"

    def test_en_returns_en(self):
        assert normalize_locale("en") == "en"

    def test_none_returns_en(self):
        assert normalize_locale(None) == "en"

    def test_integer_returns_en(self):
        assert normalize_locale(42) == "en"

    def test_unsupported_locale_returns_en(self):
        assert normalize_locale("fr") == "en"

    def test_empty_string_returns_en(self):
        assert normalize_locale("") == "en"

    def test_es_uppercase_returns_en(self):
        """Only exact 'es' matches — uppercase is rejected."""
        assert normalize_locale("ES") == "en"

    def test_boolean_returns_en(self):
        assert normalize_locale(True) == "en"

    def test_list_returns_en(self):
        assert normalize_locale(["es"]) == "en"

    def test_default_locale_constant(self):
        assert DEFAULT_LOCALE == "en"


# ---------------------------------------------------------------------------
# gemma_language_instruction
# ---------------------------------------------------------------------------


class TestGemmaLanguageInstruction:
    def test_spanish_includes_glossary(self):
        inst = gemma_language_instruction("es")
        assert "deuda estudiantil" in inst
        assert "trayectorias profesionales" in inst
        assert "perspectiva laboral" in inst
        assert "exposición a la IA" in inst

    def test_spanish_includes_prose_directive(self):
        inst = gemma_language_instruction("es")
        assert "Write all student-facing prose in Spanish" in inst

    def test_spanish_includes_json_key_preservation(self):
        inst = gemma_language_instruction("es")
        assert "JSON keys" in inst
        assert "enum values in English" in inst

    def test_spanish_includes_preservation_rules(self):
        inst = gemma_language_instruction("es")
        for phrase in [
            "official school names",
            "occupation titles",
            "BLS",
            "O*NET",
            "IPEDS",
            "BEA",
            "College Scorecard",
            "dollar amounts",
            "percentages",
        ]:
            assert phrase in inst, f"Spanish instruction missing {phrase!r}"

    def test_english_includes_preservation_rules(self):
        inst = gemma_language_instruction("en")
        assert "Preserve official school names" in inst
        assert "BLS" in inst
        assert "dollar amounts" in inst

    def test_english_does_not_include_glossary(self):
        inst = gemma_language_instruction("en")
        assert "Glossary" not in inst
        assert "deuda estudiantil" not in inst

    def test_english_does_not_include_spanish_directive(self):
        inst = gemma_language_instruction("en")
        assert "Spanish" not in inst

    def test_invalid_locale_falls_back_to_english(self):
        """gemma_language_instruction calls normalize_locale internally,
        so garbage in should produce the English instruction."""
        inst = gemma_language_instruction("fr")  # type: ignore[arg-type]
        assert "Write student-facing prose in English" in inst

    def test_spanish_and_english_are_different(self):
        en = gemma_language_instruction("en")
        es = gemma_language_instruction("es")
        assert en != es
        assert len(es) > len(en)  # Spanish has glossary, JSON rules


# ---------------------------------------------------------------------------
# fallback_text
# ---------------------------------------------------------------------------


class TestFallbackText:
    def test_gemma_unreachable_english(self):
        text = fallback_text("gemma_unreachable", "en")
        assert "unavailable" in text.lower()

    def test_gemma_unreachable_spanish(self):
        text = fallback_text("gemma_unreachable", "es")
        assert "disponible" in text.lower()

    def test_guidance_unavailable_english(self):
        text = fallback_text("guidance_unavailable", "en")
        assert "write-up" in text.lower()

    def test_guidance_unavailable_spanish(self):
        text = fallback_text("guidance_unavailable", "es")
        assert "análisis" in text.lower()

    def test_unknown_key_returns_empty_string(self):
        text = fallback_text("nonexistent_key", "en")
        assert text == ""

    def test_unknown_key_spanish_returns_empty_string(self):
        text = fallback_text("nonexistent_key", "es")
        assert text == ""

    def test_invalid_locale_falls_back_to_english(self):
        """normalize_locale is called internally — bad locale → English."""
        text = fallback_text("gemma_unreachable", "fr")  # type: ignore[arg-type]
        assert "unavailable" in text.lower()

    @pytest.mark.parametrize(
        "key",
        [
            "gemma_unreachable",
            "guidance_unavailable",
            "next_steps_unavailable",
            "boss_unknown_ai",
            "boss_unknown_loans",
            "chat_unavailable",
        ],
    )
    def test_all_keys_have_both_locales(self, key: str):
        """Every registered fallback key must have both en and es entries."""
        en = fallback_text(key, "en")
        es = fallback_text(key, "es")
        assert en, f"key {key!r} missing English fallback"
        assert es, f"key {key!r} missing Spanish fallback"
        assert en != es, f"key {key!r} has identical en/es — probably not translated"
