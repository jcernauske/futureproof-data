# Spec F3.2: Career Path Fallback — CIP Broadening + Gemma SOC Resolution

**Spec ID:** F3.2
**File:** `docs/specs/career-path-fallback.md`
**Scope:** When `get_career_paths` returns zero rows, broaden the CIP search. If broadening fails, ask Gemma to map the CIP to SOC codes and run the substitution path.
**Depends on:** B1 (routers wired), Gold tables populated
**Blocks:** Nothing — fixes a data coverage gap that causes 422s on valid school+major combos

-----

## The Problem

`POST /build/outcomes` for unitid=145813, cipcode='50.0400' (Design and Visual Communications) returns:

```
No career paths found for unitid=145813, cipcode='50.0400'.
This program may not have crosswalk coverage.
```

The existing CIP substitution logic only fires when `student_major` is provided AND the school's CIP is a broad `XX.01` code. But `50.0400` is already a 4-digit specific CIP — it just has no rows in `program_career_paths` because the CIP-SOC crosswalk doesn't cover it.

This is a data coverage hole. The crosswalk table has 626K rows but doesn't cover every CIP. Any school+major combo that hits an uncovered CIP gets a dead end instead of career paths.

The spike CLI had the same gap — it printed the error and returned `None`. The frontend shows a broken state.

-----

## The Fix

Add a two-tier fallback inside `_handle_get_career_paths` in `src/mcp_server/futureproof_server.py`, triggered when the standard path returns zero rows AND no substitution was applied.

### Tier 1: CIP Broadening (deterministic, fast)

Try progressively broader CIP codes against `program_career_paths`:

1. **Parent 4-digit CIP:** `50.0400` → try `50.04` prefix match (any row where cipcode starts with `50.04`)
2. **Family general CIP:** `50.0400` → try `50.0100` (the General code for family 50)
3. **Family 2-digit prefix:** `50.0400` → try any cipcode starting with `50.`

At each step, query `program_career_paths` for the same `unitid` with the broadened CIP. If rows come back, return them with a `data_caveat` explaining the broadening.

### Tier 2: Gemma SOC Resolution (if broadening returns nothing)

If all three broadening attempts return zero rows, the school simply has no program-level career data in this CIP family. Ask Gemma to suggest SOC codes for this CIP, then run the existing `_build_substituted_rows` path with those SOCs.

-----

## Implementation

### File: `src/mcp_server/futureproof_server.py`

#### New method: `_fallback_broaden_cip`

```python
def _fallback_broaden_cip(
    self,
    unitid: int,
    cipcode: str,
    loan_pct: float,
) -> tuple[list[dict] | None, dict | None]:
    """Try broader CIP codes when the exact cipcode has no rows.
    
    Returns (rows, caveat_dict) on success or (None, None) if all
    broadening attempts fail.
    """
    family = self._cip_family(cipcode)  # "50"
    cip4 = cipcode[:5] if len(cipcode) >= 5 else cipcode  # "50.04"
    
    # Attempt 1: Same 4-digit prefix, same school
    rows = self.query_iceberg_simple(
        CAREER_PATHS_TABLE,
        filters={"unitid": unitid},
        columns=CAREER_PATHS_RESPONSE_FIELDS,
        limit=CAREER_PATHS_SCAN_LIMIT,
    )
    prefix_rows = [r for r in rows if str(r.get("cipcode", "")).startswith(cip4)
                   and "error" not in r]
    if prefix_rows:
        caveat = {
            "type": "cip_broadened",
            "message": (
                f"No career data for CIP {cipcode} at this school. "
                f"Showing results for related programs in the {cip4} family."
            ),
            "original_cipcode": cipcode,
            "broadened_to": f"{cip4}*",
        }
        return prefix_rows, caveat

    # Attempt 2: General CIP for this family (XX.0100)
    general_cip = f"{family}.0100"
    general_rows = [r for r in rows if str(r.get("cipcode", "")) == general_cip
                    and "error" not in r]
    if general_rows:
        caveat = {
            "type": "cip_broadened",
            "message": (
                f"No career data for CIP {cipcode} at this school. "
                f"Showing results for the general {family}.0100 program."
            ),
            "original_cipcode": cipcode,
            "broadened_to": general_cip,
        }
        return general_rows, caveat

    # Attempt 3: Any CIP in this 2-digit family
    family_rows = [r for r in rows if str(r.get("cipcode", "")).startswith(f"{family}.")
                   and "error" not in r]
    if family_rows:
        caveat = {
            "type": "cip_broadened",
            "message": (
                f"No career data for CIP {cipcode} at this school. "
                f"Showing results for other programs in CIP family {family}."
            ),
            "original_cipcode": cipcode,
            "broadened_to": f"{family}.*",
        }
        return family_rows, caveat

    return None, None
```

**Performance note:** Attempt 1 does a single query and filters in Python. If `program_career_paths` is large for this unitid, this is fine at hackathon scale. For production, add SQL `LIKE` filtering.

#### New method: `_fallback_gemma_soc_resolution`

```python
def _fallback_gemma_soc_resolution(
    self,
    unitid: int,
    cipcode: str,
    program_name: str,
    loan_pct: float,
) -> tuple[list[dict] | None, dict | None]:
    """Ask Gemma to map a CIP to SOC codes when the crosswalk has no coverage.
    
    Returns (rows, caveat_dict) on success or (None, None) if Gemma
    fails or returns no usable SOCs.
    """
    from app.services import gemma_client

    system = (
        "You are a labor economist who maps academic programs to occupations.\n\n"
        f"Program: {program_name} (CIP {cipcode})\n\n"
        "List 5-10 SOC occupation codes that graduates of this program "
        "commonly enter. Use standard 6-character SOC codes (XX-XXXX format).\n\n"
        "Respond in JSON only, no preamble, no markdown:\n"
        '{"soc_codes": [{"soc": "XX-XXXX", "title": "Occupation Title"}, ...]}'
    )

    raw = gemma_client.generate(
        system=system,
        user=f"What SOC occupations do {program_name} graduates typically enter?",
        max_tokens=400,
        temperature=0.2,
    )

    if not raw:
        return None, None

    # Parse Gemma's response
    import json
    import re
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Gemma SOC resolution returned unparseable JSON: %s", cleaned[:200])
        return None, None

    soc_list = parsed.get("soc_codes", [])
    if not soc_list:
        return None, None

    # Validate SOC format and look up each in occupation_profiles
    valid_socs = [
        s["soc"] for s in soc_list
        if isinstance(s, dict) and re.match(r"^\d{2}-\d{4}$", str(s.get("soc", "")))
    ]
    if not valid_socs:
        return None, None

    # Use _build_substituted_rows with the Gemma-provided SOCs.
    # We need a slight variation: instead of fetching SOCs from the crosswalk,
    # we already have them. So we build the rows directly.
    from gold.futureproof_engine import compute_stat_ern, compute_stat_roi

    # Try to get a school earnings row for this CIP family as the basis
    family = self._cip_family(cipcode)
    co_rows = self.query_iceberg_simple(
        CAREER_OUTCOMES_TABLE,
        filters={"unitid": unitid},
        columns=_SUB_CO_FIELDS,
        limit=50,
    )
    # Find best match: exact CIP, then same family, then any
    school_row = None
    for r in co_rows:
        if "error" not in r and str(r.get("cipcode", "")) == cipcode:
            school_row = r
            break
    if school_row is None:
        for r in co_rows:
            if "error" not in r and str(r.get("cipcode", "")).startswith(f"{family}."):
                school_row = r
                break
    if school_row is None and co_rows and "error" not in co_rows[0]:
        school_row = co_rows[0]  # any row as earnings basis

    # Build rows for each valid SOC
    rows: list[dict] = []
    for soc in valid_socs:
        op_rows = self.query_iceberg_simple(
            OCCUPATION_PROFILES_TABLE,
            filters={"soc_code": soc},
            columns=_SUB_OP_FIELDS,
            limit=1,
        )
        op = op_rows[0] if op_rows and "error" not in op_rows[0] else {}
        if not op:
            continue  # SOC not in our data — skip

        onet_rows = self.query_iceberg_simple(
            ONET_WORK_PROFILES_TABLE,
            filters={"bls_soc_code": soc},
            columns=_SUB_ONET_FIELDS,
            limit=1,
        )
        onet = onet_rows[0] if onet_rows and "error" not in onet_rows[0] else {}

        ai_rows = self.query_iceberg_simple(
            AI_EXPOSURE_TABLE,
            filters={"soc_code": soc},
            columns=_SUB_AI_FIELDS,
            limit=1,
        )
        ai = ai_rows[0] if ai_rows and "error" not in ai_rows[0] else {}

        # Blend school earnings (if available) with occupation data
        row = {**op, **onet, **ai}
        if school_row:
            row["unitid"] = unitid
            row["institution_name"] = school_row.get("institution_name", "")
            row["cipcode"] = cipcode
            row["program_name"] = program_name
            row["earnings_1yr_median"] = school_row.get("earnings_1yr_median")
            row["earnings_1yr_p25"] = school_row.get("earnings_1yr_p25")
            row["earnings_1yr_p75"] = school_row.get("earnings_1yr_p75")
            row["debt_median"] = school_row.get("debt_median")
            row["debt_to_earnings_annual"] = school_row.get("debt_to_earnings_annual")
            # Compute ERN and ROI from school data
            ern = compute_stat_ern(
                school_row.get("earnings_1yr_median"),
                op.get("median_annual_wage"),
                school_row.get("cip_family_earnings_rank"),
            )
            dte = school_row.get("debt_to_earnings_annual")
            if dte is not None and 0.0 <= loan_pct < 1.0:
                dte = float(dte) * loan_pct
            roi = compute_stat_roi(dte)
            row["stat_ern"] = ern
            row["stat_roi"] = roi
        else:
            row["unitid"] = unitid
            row["cipcode"] = cipcode
            row["program_name"] = program_name

        rows.append(row)

    if not rows:
        return None, None

    # Sort by stats_available_count
    rows.sort(key=lambda r: -(r.get("stats_available_count") or 0))

    # Decode JSON struct fields
    for r in rows:
        _decode_json_struct_fields(r)

    gemma_soc_titles = ", ".join(s.get("title", s["soc"]) for s in soc_list[:5])
    caveat = {
        "type": "gemma_soc_resolution",
        "message": (
            f"No crosswalk data for CIP {cipcode} ({program_name}). "
            f"Career paths were identified by Gemma AI and may not reflect "
            f"typical graduate outcomes. Careers shown: {gemma_soc_titles}."
        ),
        "original_cipcode": cipcode,
        "gemma_socs": valid_socs,
        "ai_estimated": True,
    }
    return rows, caveat
```

#### Modify: `_handle_get_career_paths` — add fallback after the "Standard path" empty-rows check

Replace the current empty-rows block:

```python
        if not rows:
            return self.attach_governance(
                {
                    "data": None,
                    "message": (
                        f"No career paths found for unitid={unitid_value}, "
                        f"cipcode='{cipcode}'. This program may not have "
                        f"crosswalk coverage."
                    ),
                },
                CAREER_PATHS_TABLE,
            )
```

With:

```python
        if not rows:
            # ── Tier 1: CIP broadening (deterministic) ──
            broadened_rows, broadened_caveat = self._fallback_broaden_cip(
                unitid=unitid_value,
                cipcode=cipcode,
                loan_pct=loan_pct_value,
            )
            if broadened_rows:
                for r in broadened_rows:
                    _decode_json_struct_fields(r)
                broadened_rows.sort(
                    key=lambda r: (
                        -(r.get("stats_available_count") or 0),
                        str(r.get("occupation_title") or ""),
                    )
                )
                return self.enrich_response(
                    {
                        "data": broadened_rows,
                        "row_count": len(broadened_rows),
                        "substitution_applied": True,
                        "reported_cipcode": cipcode,
                        "substituted_cipcode": broadened_caveat.get("broadened_to", ""),
                        "data_caveat": broadened_caveat,
                    },
                    CAREER_PATHS_TABLE,
                )

            # ── Tier 2: Gemma SOC resolution (AI-estimated) ──
            # Look up program name for the prompt
            programs = self.query_iceberg_simple(
                CAREER_OUTCOMES_TABLE,
                filters={"unitid": unitid_value, "cipcode": cipcode},
                columns=["program_name"],
                limit=1,
            )
            prog_name = (
                str(programs[0].get("program_name", cipcode))
                if programs and "error" not in programs[0]
                else student_major or cipcode
            )
            gemma_rows, gemma_caveat = self._fallback_gemma_soc_resolution(
                unitid=unitid_value,
                cipcode=cipcode,
                program_name=prog_name,
                loan_pct=loan_pct_value,
            )
            if gemma_rows:
                return self.enrich_response(
                    {
                        "data": gemma_rows,
                        "row_count": len(gemma_rows),
                        "substitution_applied": True,
                        "reported_cipcode": cipcode,
                        "data_caveat": gemma_caveat,
                    },
                    CAREER_PATHS_TABLE,
                )

            # Both fallbacks failed — return the original empty message
            return self.attach_governance(
                {
                    "data": None,
                    "message": (
                        f"No career paths found for unitid={unitid_value}, "
                        f"cipcode='{cipcode}'. Tried CIP broadening and "
                        f"Gemma SOC resolution — no coverage available."
                    ),
                },
                CAREER_PATHS_TABLE,
            )
```

-----

## What This Changes

| Layer | File | Change |
|-------|------|--------|
| MCP Server | `src/mcp_server/futureproof_server.py` | Add `_fallback_broaden_cip()`, `_fallback_gemma_soc_resolution()`, modify `_handle_get_career_paths` empty-rows block |

Nothing else changes. The `stat_engine.py`, routers, and frontend are unaffected — they already handle `substitution_applied=True` and `data_caveat` in the response.

-----

## Data Caveat Display

The frontend already handles `data_caveat` on `CareerOutcome` (F3 spec includes a substitution notice banner). The two new caveat types (`cip_broadened` and `gemma_soc_resolution`) will render through the same path. The `gemma_soc_resolution` caveat includes `"ai_estimated": true` so the frontend can show a stronger disclaimer if desired.

-----

## What NOT to Do

- Do not modify `stat_engine.py` or any router — the fallback lives in the MCP handler where the data gap occurs.
- Do not add new Gold tables or pipeline steps — this is a runtime fallback for uncovered CIPs.
- Do not cache Gemma SOC resolutions to disk in this spec. In-memory is fine. A proper caching layer is post-hackathon.
- Do not call Gemma for Tier 1 (broadening). It's deterministic and should stay that way.

-----

## Acceptance Criteria

- [x] `unitid=145813, cipcode='50.0400'` returns career paths (via broadening or Gemma) instead of a 422
- [x] Broadened results include a `data_caveat` with `type: "cip_broadened"`
- [x] Gemma-resolved results include a `data_caveat` with `type: "gemma_soc_resolution"` and `ai_estimated: true`
- [x] If broadening finds rows, Gemma is never called (fast path)
- [x] If both fallbacks fail, the error message mentions both were attempted
- [x] Existing CIP substitution path (broad `XX.01` + `student_major`) is unchanged
- [x] Standard path (exact cipcode match with rows) is unchanged — 221 MCP tests pass

-----

*— End of Spec F3.2 —*
