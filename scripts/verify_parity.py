"""Sanity-check the rewritten data-access layer against captured fixtures.

Loads each fixture in ``tests/mcp/fixtures/career_paths_responses/``,
re-runs the handler against the live (post-rewrite) code, and diffs
the stripped response JSON byte-for-byte.

Exit 0 on full match, 1 on any divergence. The first divergence
point is printed with surrounding context.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
for p in (str(_PROJECT_ROOT / "backend"), str(_PROJECT_ROOT / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.services.mcp_client import get_server  # noqa: E402

FIXTURE_DIR = _PROJECT_ROOT / "tests" / "mcp" / "fixtures" / "career_paths_responses"


def _serialize(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


def _strip_volatile(response: dict) -> dict:
    return {k: v for k, v in response.items() if k != "governance"}


def main() -> int:
    server = get_server()
    failures: list[str] = []
    for fpath in sorted(FIXTURE_DIR.glob("*.json")):
        with fpath.open() as fh:
            fixture = json.load(fh)
        expected = fixture["response"]
        actual = _strip_volatile(server._handle_get_career_paths(fixture["input"]))
        exp_s = _serialize(expected)
        act_s = _serialize(actual)
        if exp_s == act_s:
            print(f"PASS {fpath.name}")
            continue
        failures.append(fpath.name)
        print(f"FAIL {fpath.name}")
        for i, (a, b) in enumerate(zip(exp_s, act_s)):
            if a != b:
                ctx_start = max(0, i - 80)
                ctx_end = min(max(len(exp_s), len(act_s)), i + 160)
                print(
                    f"  first divergence at char {i}\n"
                    f"  expected: ...{exp_s[ctx_start:ctx_end]!r}...\n"
                    f"  actual:   ...{act_s[ctx_start:ctx_end]!r}..."
                )
                break
        if len(exp_s) != len(act_s):
            print(f"  length delta: expected {len(exp_s)} actual {len(act_s)}")
    if failures:
        print(f"\n{len(failures)} failures: {failures}")
        return 1
    print("\nall parity fixtures match")
    return 0


if __name__ == "__main__":
    sys.exit(main())
