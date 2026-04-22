"""Capture _handle_get_career_paths response fixtures for JOIN parity test.

Run once against the UNMODIFIED fan-out implementation before the
performance-soc-retrieval rewrite touches `_build_substituted_rows`.
Fixtures are committed and replayed by
`tests/mcp/test_substituted_rows_join_parity.py` to prove the new JOIN
produces byte-identical payloads.

Usage::

    uv run python scripts/capture_career_paths_fixtures.py

Fixtures land in ``tests/mcp/fixtures/career_paths_responses/*.json``.
Each file's name encodes the input so the parity test can parameterize.
Governance metadata (``governance`` key) is stripped — it carries
timestamps and is not part of the data-layer contract under test.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_BACKEND_PATH = _PROJECT_ROOT / "backend"
_SRC_PATH = _PROJECT_ROOT / "src"
for p in (str(_BACKEND_PATH), str(_SRC_PATH)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.services.mcp_client import get_server  # noqa: E402

FIXTURE_DIR = _PROJECT_ROOT / "tests" / "mcp" / "fixtures" / "career_paths_responses"


# Fixture inputs chosen for §4 coverage. Name, then dict passed to
# _handle_get_career_paths. Some inputs intentionally fail or route
# through fallbacks — the fixture captures whatever the current
# implementation emits so the rewrite must match.
FIXTURES: list[tuple[str, dict]] = [
    # (a) UIUC (145637) + 26.01 substituted to Biology sub-CIP. Hits
    # the substituted path.
    (
        "a_uiuc_biology_substituted",
        {
            "unitid": 145637,
            "cipcode": "26.01",
            "student_major": "Biology",
        },
    ),
    # (b) IU-B (151351) + 52.01 substituted to Marketing 52.14. Hits
    # the substituted path.
    (
        "b_iu_marketing_substituted",
        {
            "unitid": 151351,
            "cipcode": "52.01",
            "student_major": "Marketing",
        },
    ),
    # (c) Small-program school. UIUC + a less-common CIP.
    (
        "c_small_program_substituted",
        {
            "unitid": 145637,
            "cipcode": "13.01",
            "student_major": "Education",
        },
    ),
    # NOTE: (d) was removed — a "substitution with no crosswalk SOCs"
    # case routes through _fallback_gemma_soc_resolution, which invokes
    # a non-deterministic LLM. Byte-parity is impossible by nature.
    # The school-CTE short-circuit is covered by fixture (e); JOIN
    # parity is covered by (a)/(b)/(c)/(f)/(g); standard path by (h).
    # (e) Missing broad-CIP earnings row: school that doesn't report
    # the reported_cipcode's 4-digit bucket. Triggers the school-CTE
    # short-circuit in the new code. We use a nonsense unitid so the
    # career_outcomes lookup is guaranteed empty.
    (
        "e_missing_school_earnings",
        {
            "unitid": 999999,
            "cipcode": "52.01",
            "student_major": "Marketing",
        },
    ),
    # (f) Wide substituted CIP where niche SOCs may have partial data
    # (op present, onet/ai missing). Nursing 51.38 has several broad
    # and specialty SOCs; onet coverage is uneven.
    (
        "f_nursing_wide_partial_op_only",
        {
            "unitid": 145637,
            "cipcode": "51.00",
            "student_major": "Nursing",
        },
    ),
    # (g) Engineering-wide CIP 14.01 → many SOCs. Some SOCs present
    # in onet but missing occupation_profiles (validates fallback to
    # onet.primary_title for occupation_title).
    (
        "g_engineering_wide_partial_onet_only",
        {
            "unitid": 145637,
            "cipcode": "14.01",
            "student_major": "Engineering",
        },
    ),
    # (h) Standard path — school that directly reports the cipcode.
    # Provides baseline for the standard-path parity.
    (
        "h_standard_path_exact",
        {
            "unitid": 151351,
            "cipcode": "52.14",
        },
    ),
]


def _strip_volatile(response: dict) -> dict:
    """Strip governance block so fixtures don't carry timestamps.

    The data-access-layer rewrite must preserve response fields, not
    governance metadata (which includes last_updated timestamps and
    would flap across captures).
    """
    out = {k: v for k, v in response.items() if k != "governance"}
    return out


def main() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    server = get_server()
    written: list[str] = []
    for name, inputs in FIXTURES:
        response = server._handle_get_career_paths(inputs)
        fixture = {
            "input": inputs,
            "response": _strip_volatile(response),
        }
        path = FIXTURE_DIR / f"{name}.json"
        path.write_text(
            json.dumps(fixture, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        written.append(
            f"  {name}.json  row_count={response.get('row_count')}  "
            f"sub={response.get('substitution_applied')}"
        )
    print(f"Wrote {len(written)} fixtures to {FIXTURE_DIR}:")
    for line in written:
        print(line)


if __name__ == "__main__":
    main()
