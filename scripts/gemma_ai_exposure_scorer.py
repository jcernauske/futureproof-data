"""Batch-score every O*NET occupation's AI exposure via Gemma 4.

This script is invoked manually, once per scoring run. It reads
``consumable.onet_work_profiles`` (798 rows) and
``consumable.occupation_profiles`` (832 rows) from the Gold zone,
calls Gemma for each occupation with a deterministic config, and
appends one JSON row per occupation to the committed output file at
``governance/fixtures/gemma-ai-exposure-scores.json``.

Inference backend is selected via ``INFERENCE_BACKEND`` in ``.env``:

* ``openrouter`` (default for this script): cloud inference via
  ``https://openrouter.ai/api/v1`` using the OpenAI SDK. ~10–15 minutes
  for 798 occupations, ~$0.21 cost. Requires ``OPENROUTER_API_KEY``.
* ``ollama``: local inference at ``OLLAMA_HOST`` (defaults to
  ``http://localhost:11434``). ~1–2 hours, free, requires the model
  pulled locally.

Both paths share the same prompt, response shape, retry loop, and
checkpoint format — the model_tag stamped on each row records which
backend produced it.

Design invariants:

* **Deterministic:** ``temperature=0`` on both backends, ``seed=42`` on
  Ollama, JSON-only response (Ollama ``format="json"`` / OpenRouter
  ``response_format={"type": "json_object"}``), pinned model tag.
* **Resumable:** a checkpoint file tracks completed SOCs. Re-running
  skips already-scored occupations and only invokes Gemma for the
  remainder. Final results are re-written after every 10 completions.
* **Retry-tolerant:** each SOC is retried up to 3× on JSON parse,
  structural validation, transient HTTP, or rate-limit (429) failures
  with [2,5,10]s backoff. Failures after 3 attempts are persisted as
  ``error`` rows for later triage.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

# Repo root for resolving fixture paths and Gold tables. NOTE: we do
# NOT mutate sys.path at import time — that pollutes test runs.
# Imports from src/ happen lazily inside run_batch().
_REPO_ROOT = Path(__file__).resolve().parent.parent

# Load .env once at module import. The cloud-gemma-deployment spec and
# gemma_client.py both follow this convention, so the scorer behaves
# the same way the production CLI does.
load_dotenv(_REPO_ROOT / ".env", override=False)

logger = logging.getLogger(__name__)


def _decode_json_field(value: object) -> object:
    """Decode a JSON-string field to a Python object.

    Inlined from ``src/gold/ai_exposure_transformer._decode_json_field``
    to avoid a `sys.path` mutation at module import time. Behavior is
    identical: non-strings pass through; invalid JSON returns as-is.
    """
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return value


# ---------------------------------------------------------------------------
# Backend configuration
# ---------------------------------------------------------------------------
#
# Mirrors backend/app/services/gemma_client.py so the scorer reads the
# same .env vars the rest of the project uses. Both backends are
# OpenAI-compatible at the API level; the difference is base_url and
# the JSON-mode flag (Ollama uses `format=json` on its native endpoint;
# OpenRouter uses the OpenAI `response_format={"type":"json_object"}`).

DEFAULT_BACKEND = "openrouter"  # batch defaults to cloud for speed/cost
DEFAULT_OPENROUTER_MODEL = "google/gemma-4-26b-a4b-it"
DEFAULT_OLLAMA_MODEL = "gemma4:26b-a4b"
DEFAULT_OLLAMA_HOST = "http://localhost:11434"

INFERENCE_BACKEND = os.getenv("INFERENCE_BACKEND", DEFAULT_BACKEND).strip().lower()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)

# The model tag stamped on every Bronze row depends on which backend
# actually served the call. Computed once at module load.
ACTIVE_MODEL_TAG = (
    OPENROUTER_MODEL if INFERENCE_BACKEND == "openrouter" else OLLAMA_MODEL
)

# Deterministic inference (Ollama-only fields). Temperature=0 applies
# to both backends; seed and num_predict are Ollama-specific options.
OLLAMA_OPTIONS: dict[str, Any] = {
    "temperature": 0.0,
    "seed": 42,
    "num_predict": 512,
}

# OpenAI / OpenRouter knobs.
OPENROUTER_MAX_TOKENS = 512
OPENROUTER_TEMPERATURE = 0.0

# Committed artifact lives under governance/ (outside .gitignore).
OUTPUT_PATH = _REPO_ROOT / "governance" / "fixtures" / "gemma-ai-exposure-scores.json"
CHECKPOINT_PATH = _REPO_ROOT / "governance" / "fixtures" / "gemma-ai-exposure-checkpoint.json"

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = (2, 5, 10)

# Rate limit between successful calls (doesn't apply during retries).
# OpenRouter is happy at ~5 RPS; the 0.5s pause stays well under that
# ceiling and matches the local Ollama cadence.
RATE_LIMIT_SECONDS = 0.5


PROMPT_TEMPLATE = """\
Given the following occupation data:

Occupation: {primary_title} (SOC: {bls_soc_code})
Top Work Activities: {top_5_activities}
Human-Edge Activities: {top_human_activities}
Burnout Factors: Time Pressure={time_pressure}/5, Work Hours={work_hours}/3
Education Typical: {education_level_name}
Median Wage: ${median_annual_wage:,}

Score this occupation's AI exposure on a 0-10 scale.

Consider:
- Which specific tasks can current AI perform or substantially assist with?
- Which tasks require physical presence, manual skill, or real-time human judgment?
- What proportion of the work is digital/screen-based vs. physical/interpersonal?
- How much would AI-augmented productivity reduce headcount demand?

Respond with ONLY a JSON object, no preamble, no markdown fences:
{{"exposure": <0-10 integer>, "rationale": "<2-3 sentences citing specific tasks>", "task_breakdown": {{"automatable": ["task1", "task2"], "human_essential": ["task3", "task4"]}}}}
"""


# ---------------------------------------------------------------------------
# Inference clients
# ---------------------------------------------------------------------------


class InferenceConfigError(RuntimeError):
    """Raised at startup when the selected backend is misconfigured."""


def _validate_backend_config() -> None:
    """Validate env vars for the selected backend; exit with a clear message."""
    if INFERENCE_BACKEND not in {"openrouter", "ollama"}:
        raise InferenceConfigError(
            f"INFERENCE_BACKEND must be 'openrouter' or 'ollama'; "
            f"got {INFERENCE_BACKEND!r}. Edit .env at the repo root."
        )
    if INFERENCE_BACKEND == "openrouter" and not OPENROUTER_API_KEY:
        raise InferenceConfigError(
            "OPENROUTER_API_KEY is required when INFERENCE_BACKEND=openrouter. "
            "Add it to .env at the repo root or switch INFERENCE_BACKEND=ollama."
        )


def _call_ollama(prompt: str, timeout: int = 180) -> str:
    """POST /api/generate against local Ollama and return the raw text."""
    resp = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "options": OLLAMA_OPTIONS,
            "format": "json",
            "stream": False,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    payload = resp.json()
    return str(payload.get("response", ""))


# Cached so we only build the OpenAI client once per process.
_openrouter_client = None


def _get_openrouter_client():
    """Return the cached OpenAI client pointed at OpenRouter."""
    global _openrouter_client
    if _openrouter_client is None:
        from openai import OpenAI  # lazy import — keeps tests cheap
        _openrouter_client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
        )
    return _openrouter_client


def _call_openrouter(prompt: str) -> str:
    """Call OpenRouter via the OpenAI SDK and return the assistant text.

    Raises ``openai.APIError`` (or subclasses such as ``RateLimitError``)
    on transport failures so the caller's retry loop can sleep and
    re-call.
    """
    client = _get_openrouter_client()
    response = client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=OPENROUTER_TEMPERATURE,
        max_tokens=OPENROUTER_MAX_TOKENS,
        response_format={"type": "json_object"},
    )
    choices = response.choices or []
    if not choices:
        return ""
    return (choices[0].message.content or "").strip()


def _call_inference(prompt: str) -> str:
    """Dispatch to the configured backend.

    Returns the raw assistant text (expected to be a JSON object). The
    caller is responsible for ``json.loads`` + structural validation;
    transient errors propagate so the retry loop catches them.
    """
    if INFERENCE_BACKEND == "openrouter":
        return _call_openrouter(prompt)
    return _call_ollama(prompt)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _assemble_prompt(onet: dict, occupation: dict) -> str:
    """Build the Gemma prompt for one occupation.

    Gold stores ``top_5_activities`` and ``top_human_activities`` as
    JSON-encoded strings; we decode them before re-serializing so the
    prompt receives a clean array rather than an escaped string.
    """
    top5 = _decode_json_field(onet.get("top_5_activities") or "[]")
    top_human = _decode_json_field(onet.get("top_human_activities") or "[]")

    if not isinstance(top5, list):
        top5 = []
    if not isinstance(top_human, list):
        top_human = []

    median_wage = occupation.get("median_annual_wage") or 0
    try:
        median_wage_int = int(median_wage)
    except (TypeError, ValueError):
        median_wage_int = 0

    return PROMPT_TEMPLATE.format(
        primary_title=onet.get("primary_title") or "Unknown occupation",
        bls_soc_code=onet.get("bls_soc_code") or "",
        top_5_activities=json.dumps(top5),
        top_human_activities=json.dumps(top_human),
        time_pressure=onet.get("time_pressure") if onet.get("time_pressure") is not None else "N/A",
        work_hours=onet.get("work_hours") if onet.get("work_hours") is not None else "N/A",
        education_level_name=occupation.get("education_level_name") or "Unknown",
        median_annual_wage=median_wage_int,
    )


def _validate_response_structure(result: Any) -> None:
    """Raise ``ValueError`` if the Gemma response is malformed."""
    if not isinstance(result, dict):
        raise ValueError(f"expected dict, got {type(result).__name__}")
    exposure = result.get("exposure")
    if not isinstance(exposure, int) or isinstance(exposure, bool):
        raise ValueError(f"exposure must be int, got {exposure!r}")
    if not 0 <= exposure <= 10:
        raise ValueError(f"exposure must be 0-10, got {exposure}")
    rationale = result.get("rationale")
    # Aligned to RAW-GAE-005 (Bronze DQ rule: 50-800 chars). Tightened
    # at the scorer to fail-fast and trigger the retry loop instead of
    # shipping a too-short rationale into Bronze where DQ catches it
    # an hour later.
    if not isinstance(rationale, str):
        raise ValueError("rationale missing")
    rlen = len(rationale.strip())
    if not (50 <= rlen <= 800):
        raise ValueError(f"rationale length must be 50-800 chars, got {rlen}")
    tb = result.get("task_breakdown")
    if not isinstance(tb, dict):
        raise ValueError("task_breakdown must be a dict")
    for key in ("automatable", "human_essential"):
        val = tb.get(key)
        if not isinstance(val, list):
            raise ValueError(f"task_breakdown.{key} must be a list")
        if not all(isinstance(x, str) for x in val):
            raise ValueError(f"task_breakdown.{key} must contain only strings")


def _is_rate_limit_error(exc: BaseException) -> bool:
    """True for known rate-limit shapes from either backend."""
    # OpenAI SDK exposes RateLimitError; HTTPError carries .response.status_code.
    name = type(exc).__name__
    if name == "RateLimitError":
        return True
    response = getattr(exc, "response", None)
    if response is not None:
        status = getattr(response, "status_code", None) or getattr(response, "status", None)
        if status == 429:
            return True
    return False


def score_occupation(onet: dict, occupation: dict) -> dict:
    """Score a single occupation with a 3-retry loop.

    Returns either a successful row (``error=None``) or an error row
    with the last-seen exception text and truncated raw response.
    Catches:
      * ``json.JSONDecodeError`` — Gemma returned non-JSON.
      * ``ValueError`` — structural validation failed.
      * ``KeyError`` / ``TypeError`` — defensive against malformed dicts.
      * ``requests.RequestException`` — Ollama transport failure.
      * ``Exception`` from ``openai`` — any OpenRouter SDK failure
        including ``RateLimitError`` (429), ``APIError``, ``Timeout``.
    """
    prompt = _assemble_prompt(onet, occupation)
    soc = onet.get("bls_soc_code") or ""
    title = onet.get("primary_title") or ""

    last_error: str | None = None
    last_raw_text: str = ""

    for attempt in range(MAX_RETRIES):
        try:
            raw_text = _call_inference(prompt)
            last_raw_text = raw_text
            result = json.loads(raw_text)
            _validate_response_structure(result)
            return {
                "soc_code": soc,
                "primary_title": title,
                "exposure_score": int(result["exposure"]),
                "rationale": result["rationale"].strip(),
                "task_breakdown_automatable": json.dumps(
                    result["task_breakdown"].get("automatable", [])
                ),
                "task_breakdown_human": json.dumps(
                    result["task_breakdown"].get("human_essential", [])
                ),
                "scoring_model": "gemma-4",
                "model_tag": ACTIVE_MODEL_TAG,
                "scored_at": datetime.now(timezone.utc).isoformat(),
                "error": None,
            }
        except (
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
            requests.RequestException,
        ) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_SECONDS[attempt])
        except Exception as exc:  # OpenRouter SDK errors (RateLimitError, APIError, …)
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < MAX_RETRIES - 1:
                # Rate limits get the longer end of the backoff schedule.
                backoff = RETRY_BACKOFF_SECONDS[attempt]
                if _is_rate_limit_error(exc):
                    backoff = max(backoff, 10)
                time.sleep(backoff)

    return {
        "soc_code": soc,
        "primary_title": title,
        "error": f"Failed after {MAX_RETRIES} attempts: {last_error}",
        "raw_response": last_raw_text[:500] if last_raw_text else None,
        "scoring_model": "gemma-4",
        "model_tag": ACTIVE_MODEL_TAG,
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------


def load_checkpoint() -> set[str]:
    """Return the set of already-scored SOC codes (empty if fresh run)."""
    if not CHECKPOINT_PATH.exists():
        return set()
    try:
        data = json.loads(CHECKPOINT_PATH.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(
            "Checkpoint at %s unreadable (%s); starting fresh",
            CHECKPOINT_PATH, exc,
        )
        return set()
    return set(data.get("completed_socs", []))


def save_checkpoint(completed_socs: set[str], results: list[dict]) -> None:
    """Persist both the checkpoint and the committed output file.

    Writes a single JSON array to ``OUTPUT_PATH`` so a mid-run crash
    leaves a usable artifact — last successful checkpoint wins.
    """
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH.write_text(json.dumps({
        "completed_socs": sorted(completed_socs),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "model_tag": ACTIVE_MODEL_TAG,
        "backend": INFERENCE_BACKEND,
    }, indent=2))
    OUTPUT_PATH.write_text(json.dumps(results, indent=2))


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------


def _load_gold_table(
    project_dir: Path, namespace: str, table: str
) -> list[dict]:
    """Read a Gold Iceberg table into a list of dicts.

    Lazy-imports ``brightsmith.infra.iceberg_setup`` so module load
    doesn't depend on the pipeline being installed (lets the unit
    tests mock-test ``score_occupation`` in isolation).
    """
    from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

    gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"
    catalog_path = project_dir / "data" / "catalog" / "catalog.db"
    catalog = get_catalog(gold_warehouse, catalog_path)
    iceberg_table = catalog.load_table(f"{namespace}.{table}")
    return read_with_duckdb(iceberg_table)


def load_onet_profiles(project_dir: Path) -> list[dict]:
    """Load O*NET work profiles (798 rows)."""
    return _load_gold_table(project_dir, "consumable", "onet_work_profiles")


def load_occupation_profiles(project_dir: Path) -> dict[str, dict]:
    """Load BLS occupation profiles keyed by SOC code (832 rows)."""
    rows = _load_gold_table(project_dir, "consumable", "occupation_profiles")
    return {r["soc_code"]: r for r in rows if r.get("soc_code")}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_batch(project_dir: Path | None = None) -> dict:
    """Score every O*NET occupation and persist to governance/fixtures/.

    Returns a summary dict with ``scored``, ``errors``, ``skipped_cached``.
    Safe to re-invoke — the checkpoint causes already-scored SOCs to
    be skipped.
    """
    _validate_backend_config()
    project_dir = Path(project_dir or _REPO_ROOT).resolve()

    logger.info(
        "Inference backend: %s | model_tag: %s",
        INFERENCE_BACKEND, ACTIVE_MODEL_TAG,
    )
    logger.info("Loading O*NET profiles from %s ...", project_dir)
    onet_profiles = load_onet_profiles(project_dir)
    occupations = load_occupation_profiles(project_dir)
    logger.info(
        "Loaded %d O*NET profiles, %d occupation profiles",
        len(onet_profiles), len(occupations),
    )

    completed = load_checkpoint()

    # Start from any existing results so we can append rather than
    # overwrite on resume.
    results: list[dict] = []
    if OUTPUT_PATH.exists():
        try:
            results = json.loads(OUTPUT_PATH.read_text())
            if not isinstance(results, list):
                results = []
        except json.JSONDecodeError:
            results = []

    errors = sum(1 for r in results if r.get("error"))
    scored = len(results) - errors
    skipped_cached = 0

    for onet in onet_profiles:
        soc = onet.get("bls_soc_code")
        if not soc:
            continue
        if soc in completed:
            skipped_cached += 1
            continue

        occupation = occupations.get(soc, {})
        title = onet.get("primary_title") or soc
        logger.info("Scoring %s (%s)...", soc, title)

        result = score_occupation(onet, occupation)
        results.append(result)
        completed.add(soc)

        if result.get("error"):
            errors += 1
            logger.warning("  error: %s", result["error"])
        else:
            scored += 1

        if len(completed) % 10 == 0:
            save_checkpoint(completed, results)

        time.sleep(RATE_LIMIT_SECONDS)

    save_checkpoint(completed, results)

    summary = {
        "total_rows": len(results),
        "scored": scored,
        "errors": errors,
        "skipped_cached": skipped_cached,
        "error_rate_pct": (100.0 * errors / len(results)) if results else 0.0,
        "backend": INFERENCE_BACKEND,
        "model_tag": ACTIVE_MODEL_TAG,
        "output_path": str(OUTPUT_PATH),
    }
    logger.info("Batch complete: %s", summary)
    return summary


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(message)s",
    )
    try:
        run_batch()
    except InferenceConfigError as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)
