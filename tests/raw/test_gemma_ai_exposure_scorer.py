"""Tests for scripts/gemma_ai_exposure_scorer.

Covers JSON response parsing, structural validation, JSON field
decoding in prompt assembly, the 3-retry loop with backoff, and the
deterministic Ollama config. Ollama is mocked — no network.
"""

import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock, patch


_SCORER_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "scripts"
    / "gemma_ai_exposure_scorer.py"
)
_SPEC = importlib.util.spec_from_file_location("gemma_scorer", _SCORER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

score_occupation = _MOD.score_occupation
_assemble_prompt = _MOD._assemble_prompt
_validate_response_structure = _MOD._validate_response_structure


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


SAMPLE_ONET = {
    "bls_soc_code": "13-2051",
    "primary_title": "Financial Analysts",
    # Gold stores these as JSON-encoded strings — the scorer decodes.
    "top_5_activities": json.dumps(
        [{"activity": "Processing data", "importance": 4.5}]
    ),
    "top_human_activities": json.dumps(
        [{"activity": "Client relationships", "importance": 4.0}]
    ),
    "time_pressure": 3.5,
    "work_hours": 2.0,
}

SAMPLE_OCCUPATION = {
    "education_level_name": "Bachelor's degree",
    "median_annual_wage": 95570,
}

VALID_GEMMA_RESPONSE = {
    "exposure": 7,
    "rationale": "Financial analysts process data, run models, and generate reports using widely-available AI-automatable tools.",
    "task_breakdown": {
        "automatable": ["Data aggregation", "Report generation"],
        "human_essential": ["Client relationship management", "Judgment calls"],
    },
}


def _mock_ollama_response(body: dict | str):
    """Build a fake requests.post response object."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value={
        "response": body if isinstance(body, str) else json.dumps(body),
    })
    return resp


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------


class TestPromptAssembly:
    def test_json_fields_decoded_not_double_encoded(self):
        """top_5_activities / top_human_activities decoded before re-encoding."""
        prompt = _assemble_prompt(SAMPLE_ONET, SAMPLE_OCCUPATION)
        # Double-encoding would produce '"[{\\"activity\\": ...}]"' —
        # the ``\\"`` is the giveaway. Require the decoded form.
        assert '\\"activity\\"' not in prompt
        assert '"activity"' in prompt

    def test_prompt_contains_key_fields(self):
        prompt = _assemble_prompt(SAMPLE_ONET, SAMPLE_OCCUPATION)
        assert "Financial Analysts" in prompt
        assert "13-2051" in prompt
        assert "Bachelor's degree" in prompt
        # Wage is formatted with commas.
        assert "$95,570" in prompt

    def test_prompt_handles_missing_onet_fields(self):
        """Missing activities / context fields don't crash prompt assembly."""
        bare = {"bls_soc_code": "99-9999", "primary_title": None}
        prompt = _assemble_prompt(bare, {})
        assert "99-9999" in prompt
        assert "Unknown occupation" in prompt


# ---------------------------------------------------------------------------
# Response validation
# ---------------------------------------------------------------------------


class TestResponseValidation:
    def test_valid_response_passes(self):
        _validate_response_structure(VALID_GEMMA_RESPONSE)

    def test_non_dict_rejected(self):
        import pytest
        with pytest.raises(ValueError):
            _validate_response_structure(["not", "a", "dict"])

    def test_exposure_out_of_range_rejected(self):
        import pytest
        bad = dict(VALID_GEMMA_RESPONSE, exposure=11)
        with pytest.raises(ValueError):
            _validate_response_structure(bad)

    def test_exposure_non_int_rejected(self):
        import pytest
        bad = dict(VALID_GEMMA_RESPONSE, exposure=7.5)
        with pytest.raises(ValueError):
            _validate_response_structure(bad)

    def test_short_rationale_rejected(self):
        """Rationale shorter than the 50-char Bronze DQ floor is rejected."""
        import pytest
        bad = dict(VALID_GEMMA_RESPONSE, rationale="short")
        with pytest.raises(ValueError, match="50-800"):
            _validate_response_structure(bad)

    def test_overlong_rationale_rejected(self):
        """Rationale beyond 800 chars violates the Bronze DQ ceiling."""
        import pytest
        bad = dict(VALID_GEMMA_RESPONSE, rationale="x" * 801)
        with pytest.raises(ValueError, match="50-800"):
            _validate_response_structure(bad)

    def test_missing_rationale_rejected(self):
        import pytest
        bad = dict(VALID_GEMMA_RESPONSE)
        del bad["rationale"]
        with pytest.raises(ValueError):
            _validate_response_structure(bad)

    def test_task_breakdown_missing_key_rejected(self):
        import pytest
        bad = dict(VALID_GEMMA_RESPONSE, task_breakdown={"automatable": []})
        with pytest.raises(ValueError):
            _validate_response_structure(bad)


# ---------------------------------------------------------------------------
# score_occupation (happy path)
# ---------------------------------------------------------------------------


def _stub_inference(response: dict | str):
    """Build a backend-agnostic stub for ``_call_inference``.

    Returns the JSON-encoded response (matching what either backend
    would yield after format=json / response_format=json_object).
    """
    text = response if isinstance(response, str) else json.dumps(response)
    return lambda _prompt: text


class TestScoreOccupationHappyPath:
    def test_returns_successful_row_shape(self):
        """Backend-agnostic happy path via patched _call_inference."""
        with patch.object(_MOD, "_call_inference",
                          side_effect=_stub_inference(VALID_GEMMA_RESPONSE)):
            result = score_occupation(SAMPLE_ONET, SAMPLE_OCCUPATION)

        assert result["soc_code"] == "13-2051"
        assert result["primary_title"] == "Financial Analysts"
        assert result["exposure_score"] == 7
        assert result["scoring_model"] == "gemma-4"
        assert result["model_tag"]  # populated for whichever backend
        assert result["error"] is None
        # Task breakdown is JSON-serialized for Iceberg.
        automatable = json.loads(result["task_breakdown_automatable"])
        assert automatable == ["Data aggregation", "Report generation"]

    def test_ollama_call_sends_deterministic_config(self):
        """When INFERENCE_BACKEND=ollama: temperature=0, seed=42, format=json."""
        captured = {}

        def _fake_post(url, json=None, timeout=None, **_):
            captured.update({"url": url, "body": json})
            return _mock_ollama_response(VALID_GEMMA_RESPONSE)

        # Exercise _call_ollama directly so this test is independent of
        # the active INFERENCE_BACKEND.
        with patch.object(_MOD.requests, "post", side_effect=_fake_post):
            _MOD._call_ollama("test prompt")

        body = captured["body"]
        assert body["format"] == "json"
        assert body["stream"] is False
        assert body["options"]["temperature"] == 0.0
        assert body["options"]["seed"] == 42


# ---------------------------------------------------------------------------
# Retry loop
# ---------------------------------------------------------------------------


class TestRetryLoop:
    def test_retries_on_json_decode_failure(self):
        """Malformed JSON is retried; a valid later response is accepted."""
        texts = ["not json at all", "still {broken", json.dumps(VALID_GEMMA_RESPONSE)]
        call_iter = iter(texts)

        with patch.object(_MOD, "_call_inference",
                          side_effect=lambda _p: next(call_iter)), \
                patch.object(_MOD.time, "sleep"):  # skip backoff
            result = score_occupation(SAMPLE_ONET, SAMPLE_OCCUPATION)

        assert result["error"] is None
        assert result["exposure_score"] == 7

    def test_error_row_after_exhausted_retries(self):
        """All 3 retries fail → error row with raw_response captured."""
        texts = ["not json", "still not", "nope"]
        call_iter = iter(texts)

        with patch.object(_MOD, "_call_inference",
                          side_effect=lambda _p: next(call_iter)), \
                patch.object(_MOD.time, "sleep"):
            result = score_occupation(SAMPLE_ONET, SAMPLE_OCCUPATION)

        assert result["error"]
        assert "after 3 attempts" in result["error"]
        assert result["raw_response"] is not None

    def test_retries_on_structural_validation(self):
        """Well-formed JSON with bad structure is also retried."""
        bad = {"exposure": 20, "rationale": "x", "task_breakdown": {}}
        texts = [json.dumps(bad), json.dumps(bad), json.dumps(VALID_GEMMA_RESPONSE)]
        call_iter = iter(texts)

        with patch.object(_MOD, "_call_inference",
                          side_effect=lambda _p: next(call_iter)), \
                patch.object(_MOD.time, "sleep"):
            result = score_occupation(SAMPLE_ONET, SAMPLE_OCCUPATION)

        assert result["error"] is None

    def test_retries_on_rate_limit(self):
        """Simulated 429 RateLimitError triggers retry; success after recovers."""
        # Build a synthetic exception class named RateLimitError so the
        # _is_rate_limit_error helper recognizes it without importing
        # the real openai package.
        class FakeRateLimitError(Exception):
            pass
        FakeRateLimitError.__name__ = "RateLimitError"

        calls = [
            FakeRateLimitError("rate limited"),
            json.dumps(VALID_GEMMA_RESPONSE),
        ]

        def _side_effect(_prompt):
            val = calls.pop(0)
            if isinstance(val, BaseException):
                raise val
            return val

        with patch.object(_MOD, "_call_inference", side_effect=_side_effect), \
                patch.object(_MOD.time, "sleep"):
            result = score_occupation(SAMPLE_ONET, SAMPLE_OCCUPATION)

        assert result["error"] is None
        assert result["exposure_score"] == 7


# ---------------------------------------------------------------------------
# Backend dispatch
# ---------------------------------------------------------------------------


class TestBackendDispatch:
    def test_validate_backend_rejects_unknown(self, monkeypatch):
        """INFERENCE_BACKEND must be 'openrouter' or 'ollama'."""
        import pytest
        monkeypatch.setattr(_MOD, "INFERENCE_BACKEND", "claude")
        with pytest.raises(_MOD.InferenceConfigError, match="openrouter.*ollama"):
            _MOD._validate_backend_config()

    def test_validate_backend_requires_openrouter_key(self, monkeypatch):
        """Missing OPENROUTER_API_KEY → InferenceConfigError on openrouter."""
        import pytest
        monkeypatch.setattr(_MOD, "INFERENCE_BACKEND", "openrouter")
        monkeypatch.setattr(_MOD, "OPENROUTER_API_KEY", "")
        with pytest.raises(_MOD.InferenceConfigError, match="OPENROUTER_API_KEY"):
            _MOD._validate_backend_config()

    def test_validate_backend_ollama_no_key_required(self, monkeypatch):
        """INFERENCE_BACKEND=ollama doesn't need OPENROUTER_API_KEY."""
        monkeypatch.setattr(_MOD, "INFERENCE_BACKEND", "ollama")
        monkeypatch.setattr(_MOD, "OPENROUTER_API_KEY", "")
        # Should not raise.
        _MOD._validate_backend_config()

    def test_call_inference_dispatches_to_openrouter(self, monkeypatch):
        """When backend=openrouter: _call_inference → _call_openrouter."""
        monkeypatch.setattr(_MOD, "INFERENCE_BACKEND", "openrouter")
        with patch.object(_MOD, "_call_openrouter",
                          return_value="openrouter-result") as mock_or, \
                patch.object(_MOD, "_call_ollama") as mock_ollama:
            result = _MOD._call_inference("test prompt")
        assert result == "openrouter-result"
        mock_or.assert_called_once_with("test prompt")
        mock_ollama.assert_not_called()

    def test_call_inference_dispatches_to_ollama(self, monkeypatch):
        """When backend=ollama: _call_inference → _call_ollama."""
        monkeypatch.setattr(_MOD, "INFERENCE_BACKEND", "ollama")
        with patch.object(_MOD, "_call_ollama",
                          return_value="ollama-result") as mock_ollama, \
                patch.object(_MOD, "_call_openrouter") as mock_or:
            result = _MOD._call_inference("test prompt")
        assert result == "ollama-result"
        mock_ollama.assert_called_once_with("test prompt")
        mock_or.assert_not_called()

    def test_is_rate_limit_error_recognizes_429_via_response(self):
        """HTTPError with response.status_code=429 → True."""
        class FakeResponse:
            status_code = 429
        class FakeHTTPError(Exception):
            response = FakeResponse()
        assert _MOD._is_rate_limit_error(FakeHTTPError())

    def test_is_rate_limit_error_recognizes_by_class_name(self):
        """An exception class named RateLimitError → True (openai SDK shape)."""
        class FakeRateLimitError(Exception):
            pass
        FakeRateLimitError.__name__ = "RateLimitError"
        assert _MOD._is_rate_limit_error(FakeRateLimitError())

    def test_is_rate_limit_error_false_for_unrelated(self):
        assert not _MOD._is_rate_limit_error(ValueError("nope"))


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------


class TestCheckpoint:
    def test_load_checkpoint_missing_returns_empty_set(self, tmp_path, monkeypatch):
        fake_path = tmp_path / "no-such-checkpoint.json"
        monkeypatch.setattr(_MOD, "CHECKPOINT_PATH", fake_path)
        assert _MOD.load_checkpoint() == set()

    def test_save_and_reload_checkpoint(self, tmp_path, monkeypatch):
        checkpoint = tmp_path / "checkpoint.json"
        output = tmp_path / "scores.json"
        monkeypatch.setattr(_MOD, "CHECKPOINT_PATH", checkpoint)
        monkeypatch.setattr(_MOD, "OUTPUT_PATH", output)

        _MOD.save_checkpoint({"13-2051", "15-1252"}, [{"soc_code": "13-2051"}])
        assert checkpoint.exists()
        assert output.exists()

        assert _MOD.load_checkpoint() == {"13-2051", "15-1252"}
        # Fixture is written as a committed JSON array.
        assert json.loads(output.read_text()) == [{"soc_code": "13-2051"}]

    def test_corrupted_checkpoint_recovers_gracefully(self, tmp_path, monkeypatch):
        checkpoint = tmp_path / "checkpoint.json"
        checkpoint.write_text("this is not json {")
        monkeypatch.setattr(_MOD, "CHECKPOINT_PATH", checkpoint)
        # Should not raise — scorer logs a warning and starts fresh.
        assert _MOD.load_checkpoint() == set()
