"""Regenerate MCP substitution-path parity fixtures.

Per docs/specs/roi-net-lifetime-value.md §4 Authorized Test Modifications:
the substitution-path now drops the loan_pct scaling, sets boss_loans_sub
to None, and emits the new lifetime_earnings_15yr / roi_raw_multiplier /
roi_multiplier_basis columns. Three captured fixtures need refreshing:

  - b_iu_marketing_substituted (substitution path)
  - f_nursing_wide_partial_op_only (substitution path)
  - h_standard_path_exact (standard path now carries new ROI columns)

Three other fixtures (a, c, e, g) still match exactly because their
substitution row has no roi_raw_multiplier in Gold (cost data missing)
so the new columns are just None additions that happen to round-trip
unchanged through the JSON snapshot.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import brightsmith.config

brightsmith.config.configure(
    project_root=PROJECT_ROOT,
    require_human_approval=False,
)

from mcp_server.futureproof_server import FutureProofMCPServer

ROOT = Path("/Users/jcernauske/code/bright/futureproof-data")
FIXTURE_DIR = ROOT / "tests" / "mcp" / "fixtures" / "career_paths_responses"
VOLATILE_KEYS = {"governance", "trace_id", "request_id", "timestamp"}

server = FutureProofMCPServer(
    warehouse_path=str(ROOT / "data" / "warehouse"),
    catalog_path=str(ROOT / "data" / "catalog" / "catalog.db"),
    server_name="parity-regen",
)


def strip_volatile(obj):
    if isinstance(obj, dict):
        return {
            k: strip_volatile(v) for k, v in obj.items() if k not in VOLATILE_KEYS
        }
    if isinstance(obj, list):
        return [strip_volatile(v) for v in obj]
    return obj


def serialize(obj) -> str:
    return json.dumps(obj, indent=2, default=str, sort_keys=True) + "\n"


for fixture_id in (
    "a_uiuc_biology_substituted",
    "b_iu_marketing_substituted",
    "c_small_program_substituted",
    "e_missing_school_earnings",
    "f_nursing_wide_partial_op_only",
    "g_engineering_wide_partial_onet_only",
    "h_standard_path_exact",
):
    fp = FIXTURE_DIR / f"{fixture_id}.json"
    cur = json.loads(fp.read_text())
    inp = cur["input"]
    new_response = server._handle_get_career_paths(inp)
    out = {"input": inp, "response": strip_volatile(new_response)}
    fp.write_text(serialize(out))
    data = new_response.get("data") or []
    print(f"Regenerated {fixture_id}: {len(data)} rows")
