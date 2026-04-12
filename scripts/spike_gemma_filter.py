#!/usr/bin/env python
"""Spike B — Gemma query-time filter feasibility.

Calls get_career_paths(151351, "52.01") — IU-Bloomington Business/Commerce
General — and applies three intent filters (marketing, finance, HR) using a
simple keyword heuristic over SOC title + SOC major group name. Prints the
results as markdown tables plus a summary assessment.

Throwaway. Read-only. Does NOT modify production code or data.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mcp_server.futureproof_server import FutureProofMCPServer  # noqa: E402


UNITID = 151351  # Indiana University-Bloomington
CIPCODE = "52.01"  # Business/Commerce, General

# ---------------------------------------------------------------------------
# Intent filters — keyword heuristic + SOC-prefix short list
# ---------------------------------------------------------------------------

INTENTS: dict[str, dict] = {
    "marketing": {
        "keywords": [
            "marketing",
            "advertising",
            "sales",
            "public relations",
            "market research",
            "promotion",
            "brand",
        ],
        # SOC prefixes known to be marketing-adjacent:
        #   11-2021 Marketing Managers
        #   11-2022 Sales Managers
        #   11-2032 Public Relations & Fundraising Managers
        #   13-1161 Market Research Analysts
        #   27-3031 Public Relations Specialists
        #   41-xxxx Sales & Related (whole major group)
        "soc_prefixes": ["11-2021", "11-2022", "11-2032", "13-1161", "27-3031", "41-"],
    },
    "finance": {
        "keywords": [
            "financial",
            "finance",
            "treasur",
            "budget",
            "credit",
            "investment",
            "loan",
            "accountant",
            "accounting",
            "auditor",
            "actuarial",
        ],
        # 11-3031 Financial Managers
        # 13-2xxx Financial Specialists major minor group
        "soc_prefixes": ["11-3031", "13-2"],
    },
    "hr": {
        "keywords": [
            "human resources",
            "human-resources",
            "personnel",
            "training and development",
            "compensation",
            "benefits",
            "labor relations",
            "recruit",
        ],
        # 11-3111 Compensation & Benefits Managers
        # 11-3121 Human Resources Managers
        # 11-3131 Training & Development Managers
        # 13-1071 HR Specialists
        # 13-1075 Labor Relations Specialists
        # 13-1141 Compensation/Benefits Analysts
        # 13-1151 Training & Development Specialists
        "soc_prefixes": [
            "11-3111",
            "11-3121",
            "11-3131",
            "13-1071",
            "13-1075",
            "13-1141",
            "13-1151",
        ],
    },
}


def matches_intent(row: dict, intent: dict) -> tuple[bool, str]:
    """Return (matched, reason). Reason is 'keyword:X', 'prefix:Y', or ''."""
    title = (row.get("occupation_title") or "").lower()
    group = (row.get("soc_major_group_name") or "").lower()
    soc = row.get("soc_code") or ""
    haystack = f"{title} || {group}"
    for kw in intent["keywords"]:
        if kw in haystack:
            return True, f"kw:{kw}"
    for prefix in intent["soc_prefixes"]:
        if soc.startswith(prefix):
            return True, f"soc:{prefix}"
    return False, ""


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def banner(label: str) -> None:
    bar = "=" * 78
    print(f"\n{bar}\n{label}\n{bar}")


def md_table_full(rows: list[dict]) -> str:
    """Full career-path listing as a markdown table."""
    lines = [
        "| SOC | Occupation | SOC Major Group |",
        "|---|---|---|",
    ]
    for r in rows:
        soc = r.get("soc_code") or ""
        title = (r.get("occupation_title") or "").replace("|", "/")
        group = (r.get("soc_major_group_name") or "").replace("|", "/")
        lines.append(f"| {soc} | {title} | {group} |")
    return "\n".join(lines)


def md_table_filter(
    rows: list[dict], intent_name: str, intent: dict
) -> tuple[str, list[dict], list[dict]]:
    """Render a kept/dropped markdown table. Returns (md, kept, dropped)."""
    kept: list[dict] = []
    dropped: list[dict] = []
    lines_kept = [
        f"**{intent_name} — KEPT**",
        "",
        "| SOC | Occupation | SOC Major Group | Why |",
        "|---|---|---|---|",
    ]
    lines_drop = [
        "",
        f"**{intent_name} — DROPPED**",
        "",
        "| SOC | Occupation | SOC Major Group |",
        "|---|---|---|",
    ]
    for r in rows:
        ok, reason = matches_intent(r, intent)
        soc = r.get("soc_code") or ""
        title = (r.get("occupation_title") or "").replace("|", "/")
        group = (r.get("soc_major_group_name") or "").replace("|", "/")
        if ok:
            kept.append(r)
            lines_kept.append(f"| {soc} | {title} | {group} | {reason} |")
        else:
            dropped.append(r)
            lines_drop.append(f"| {soc} | {title} | {group} |")
    if len(kept) == 0:
        lines_kept.append("| — | *(nothing survived)* | — | — |")
    if len(dropped) == 0:
        lines_drop.append("| — | *(nothing dropped)* | — |")
    return "\n".join(lines_kept + lines_drop), kept, dropped


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run() -> int:
    server = FutureProofMCPServer(
        warehouse_path=str(PROJECT_ROOT / "data" / "warehouse"),
        catalog_path=str(PROJECT_ROOT / "data" / "catalog" / "catalog.db"),
        server_name="futureproof",
    )

    banner(f"get_career_paths(unitid={UNITID}, cipcode={CIPCODE!r})")
    resp = server._handle_get_career_paths(
        {"unitid": UNITID, "cipcode": CIPCODE}
    )
    rows = resp.get("data") or []
    print(f"{len(rows)} career paths returned")
    if not rows:
        print("nothing came back; abort")
        print(resp.get("message"))
        return 1

    banner("FULL LIST")
    print(md_table_full(rows))

    results: dict[str, tuple[list[dict], list[dict]]] = {}
    for name, intent in INTENTS.items():
        banner(f"FILTER: {name}")
        md, kept, dropped = md_table_filter(rows, name, intent)
        print(md)
        results[name] = (kept, dropped)

    banner("SUMMARY")
    print(f"Total career paths: {len(rows)}")
    for name, (kept, dropped) in results.items():
        print(f"  {name:<10} kept={len(kept):>2}  dropped={len(dropped):>2}")

    return 0


if __name__ == "__main__":
    import traceback

    try:
        sys.exit(run())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
