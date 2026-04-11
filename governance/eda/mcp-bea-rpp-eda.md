# EDA Report: mcp-bea-rpp

**Spec:** `docs/specs/mcp-bea-rpp.md`
**Zone:** MCP (AI-Ready)
**Date:** 2026-04-11
**Agent:** @data-analyst
**Eval set:** `data/ai_ready/eval/mcp-bea-rpp-eval.jsonl` (65 cases)
**Gold source:** `consumable.regional_price_parities` (51 rows, data_year=2024)
**MCP tools analyzed:** `get_regional_price_parity`, `compare_purchasing_power`

---

## Domain Context

The MCP zone does not ingest new data — it exposes the already-signed-off
`consumable.regional_price_parities` Gold table through two read-only tools so
Gemma can adjust any salary figure it presents to a student to that student's
selected state.

- **Primary entity:** US state (50 states + DC = 51 rows) at a single snapshot
  (`data_year = 2024`).
- **Grain:** one row per US state.
- **Verification taxonomy:** `verification_status` is a 2-value enum —
  `bea_official` for the 8 states the BEA spot-check table directly verifies,
  and `estimate` for the remaining 43 derived from the same raw feed but not
  individually BEA-verified.
- **Strict mode (`verified_only: true`):** refuses `estimate` rows with a
  structured null response so regulated callers can get BEA-authoritative
  values only.

---

## Key Findings

1. **All 65 eval cases pass against the live MCP server** (65/65). Both tools
   were exercised in-process through `FutureProofMCPServer._handle_*` against
   the actual Iceberg warehouse at `data/catalog/catalog.db`, and every
   `verification_key` assertion (`message_contains` + dotted-path equality)
   matched.
2. **All 8 BEA spot-check rows match Gold byte-for-byte** across every exposed
   field — `state_name`, `state_abbr`, `state_fips`, `census_region`,
   `rpp_all_items`, full-precision `purchasing_power_multiplier`, `cost_tier`,
   all four `adjusted_Nk` values, `data_source` and `data_year`.
3. **Strict-mode behavior is exhaustive, not just sampled.** The spec's
   "refuses all 43 estimates, succeeds for all 8 verified" criterion was
   verified by probing every one of the 51 states with `verified_only=true` on
   the live server. Result: 8/8 succeed (exactly the `bea_official` set),
   43/43 refuse (exactly the `estimate` set), zero cross-contamination. The
   eval file only covers 5 of the 43 refusals and 8 of the 8 successes, which
   is within spec — full exhaustive coverage belongs to tests, not the eval
   set.
4. **`compare_purchasing_power` arithmetic is byte-for-byte reproducible** at
   full precision. For all 7 success cases (CA/IA at 30K/50K/65K/75K/100K,
   plus the names and FIPS input-form variants at 65K), re-running
   `round(salary * ppm, 2)` off the Gold row reproduces the exact
   `adjusted_salary`, `difference`, and `difference_pct` in the
   `expected_output` / `verification_key`. The pre-review Advisory #1
   requirement (full-precision `purchasing_power_multiplier` exposed so the
   caller can reconstruct the arithmetic) is honored — eval rows carry
   `0.9033423667570009` for CA and `1.1389521640091116` for IA, matching Gold.
5. **No acceptance-criterion gaps.** Every one of the 11 spec requirement
   categories is represented. Category 3 ("all 3 input forms for a
   representative state") is satisfied by `form-california-fips`,
   `form-california-usps`, `form-california-name`. Category 4
   (case-insensitive) is covered by five California variants including
   whitespace-trimmed `  California  `.
6. **No tool raises on malformed input.** Every edge case exercised on the
   live server (None, bool, int, float, list, NaN, inf, missing keys,
   stripped-zero FIPS, out-of-range FIPS like `99`/`03`/`00`) returned a
   structured null response with a human-readable message — no exceptions.

---

## Eval Set Profile

### Case distribution by tool

| Tool | Cases | Share |
|------|-------|-------|
| `get_regional_price_parity` | 42 | 64.6% |
| `compare_purchasing_power` | 23 | 35.4% |
| **Total** | **65** | — |

### `get_regional_price_parity` sub-distribution (42 cases)

| Bucket | Cases | Notes |
|--------|-------|-------|
| `verified-*` — 8 BEA spot-check states, full payload | 8 | AR, CA, DC, HI, IA, MS, NJ, OK |
| `estimate-*` — sample of estimates (spec minimum = 5) | 8 | AK, AL, AZ, CO, CT, TX, NY, WA |
| `form-california-*` — all 3 input forms (fips/usps/name) | 3 | `06`, `CA`, `California` |
| `caseins-*` — case / whitespace variants | 5 | `ca`, `CA`, `california`, `CALIFORNIA`, `  California  ` |
| `strict-ok-*` — strict mode positive (all 8 BEA) | 8 | AR, CA, DC, HI, IA, MS, NJ, OK |
| `strict-refuse-*` — strict mode estimate refusals | 5 | TX, NY, WA, FL, IL |
| `unknown-*` — input rejection | 5 | `Xanadu`, `Puerto Rico`, `PR`, `''`, `'   '` |

### `compare_purchasing_power` sub-distribution (23 cases)

| Bucket | Cases | Notes |
|--------|-------|-------|
| `compare-ca-ia-*` — 5 salary points | 5 | 30K, 50K, 65K, 75K, 100K |
| `compare-names-65k`, `compare-fips-65k` — input-form variants | 2 | `California`/`Iowa`, `06`/`19` |
| `compare-bad-salary-*` — salary validation | 7 | `-5`, `0`, `10_000_000`, `20_000_000`, `'65000'`, `None`, `True` |
| `compare-same-*` — same-state rejection | 3 | `CA`/`CA`, `CA`/`California`, `06`/`CA` |
| `compare-strict-refuse-*` — mixed-provenance refusals | 4 | `CA`/`TX`, `TX`/`CA`, `NJ`/`NY`, `IA`/`FL` |
| `compare-unknown-*` — unknown state in position A or B | 2 | `Xanadu`, `Atlantis` |

### State coverage across all positive responses

- **States tested in positive responses:** 16 of 51 — AK, AL, AR, AZ, CA,
  CO, CT, DC, HI, IA, MS, NJ, NY, OK, TX, WA.
- **States never tested with a positive response:** 35 — DE, FL, GA, ID, IL,
  IN, KS, KY, LA, MA, MD, ME, MI, MN, MO, MT, NC, ND, NE, NH, NM, NV, OH, OR,
  PA, RI, SC, SD, TN, UT, VA, VT, WI, WV, WY.
- FL and IL appear only in `strict-refuse-*` refusal cases; WA, NY, TX appear
  in both `estimate-*` and `strict-refuse-*`.

This is not a coverage gap per se — exhaustive 51-state coverage belongs to
the test suite, not the eval set, and the eval covers exactly the 11 spec
categories. It is surfaced here for downstream awareness.

---

## Coverage of Spec's 11 Eval Categories

| # | Category | Required | Present | Cases |
|---|----------|----------|---------|-------|
| 1 | All 8 BEA-verified states with full expected payloads | 8 | 8 | `verified-ar..ok` |
| 2 | ≥ 5 estimated states with `data_source='estimate'` | 5 | 8 | `estimate-ak..wa` |
| 3 | All 3 input forms for representative state | 3 | 3 | `form-california-{fips,usps,name}` |
| 4 | Case-insensitive input forms | ≥ 1 | 5 | `caseins-ca-19..23` |
| 5 | Strict mode positive cases (all BEA) | ≥ 1 | 8 | `strict-ok-ar..ok` |
| 6 | Strict mode refusal cases (estimates) | ≥ 1 | 5 | `strict-refuse-tx,ny,wa,fl,il` |
| 7 | Unknown state rejection | ≥ 1 | 5 | `unknown-xanadu,puerto-rico,pr-usps,empty,whitespace` |
| 8 | `compare_purchasing_power` success at common salary levels | 4 of {30K,50K,75K,100K,65K} | 7 (all 5 + names + fips) | `compare-ca-ia-30000..100000`, `compare-names-65k`, `compare-fips-65k` |
| 9 | `compare_purchasing_power` salary validation (neg/zero/>10M/non-numeric) | 4 | 7 | `compare-bad-salary-{negative,zero,at-max,over-max,string,none,bool-true}` |
| 10 | `compare_purchasing_power` same-state rejection | ≥ 1 | 3 | `compare-same-{usps-same,usps-vs-name,fips-vs-usps}` |
| 11 | `compare_purchasing_power` strict-mode mixed-provenance refusal | ≥ 1 | 4 | `compare-strict-refuse-{ca-tx,tx-ca,nj-ny,ia-fl}` |

**All 11 categories covered at or above the spec minimum.**

Noteworthy design choices embedded in the eval set:

- Category 10 includes `compare-same-usps-vs-name` (`CA` vs `California`) and
  `compare-same-fips-vs-usps` (`06` vs `CA`) — these verify that same-state
  detection happens *after* normalization, not on raw strings. The live tool
  correctly rejects both post-normalization.
- Category 9 adds two Python-specific edge cases the spec doesn't explicitly
  enumerate but the `_validate_salary` implementation guards against:
  `None` and `True` (bool, a subclass of int). Both refuse cleanly on the
  live server.
- Strict-mode refusal cases in both tools assert only
  `message_contains: ["estimate", <state name>]` or `["Strict mode", <state name>]`
  — i.e., they pin identification of the offending state without freezing
  exact wording, which is the right level of brittleness for NL messages.

---

## Tool Response Verification

### `get_regional_price_parity`: BEA spot-check row parity (8/8)

For each of the 8 `bea_official` rows, the eval's `expected_output.data`
matches the Gold row byte-for-byte across 12 fields (`state_name`,
`state_abbr`, `state_fips`, `census_region`, `rpp_all_items`,
`purchasing_power_multiplier`, `cost_tier`, `adjusted_30k`, `adjusted_50k`,
`adjusted_75k`, `adjusted_100k`, `data_source==verification_status`,
`data_year`).

| Abbr | State | rpp_all_items | ppm (full precision) | cost_tier | adj_50k | Match |
|------|-------|---------------|----------------------|-----------|---------|-------|
| AR | Arkansas | 86.9 | 1.1507479861910241 | very_low | 57537.4 | OK |
| CA | California | 110.7 | 0.9033423667570009 | very_high | 45167.12 | OK |
| DC | District of Columbia | 109.9 | 0.9099181073703366 | very_high | 45495.91 | OK |
| HI | Hawaii | 110.0 | 0.9090909090909091 | very_high | 45454.55 | OK |
| IA | Iowa | 87.8 | 1.1389521640091116 | very_low | 56947.61 | OK |
| MS | Mississippi | 87.0 | 1.1494252873563218 | very_low | 57471.26 | OK |
| NJ | New Jersey | 108.8 | 0.9191176470588236 | very_high | 45955.88 | OK |
| OK | Oklahoma | 87.8 | 1.1389521640091116 | very_low | 56947.61 | OK |

### Strict-mode exhaustive sweep (51/51)

Probed every Gold row with `verified_only=true`:

- **Succeeded:** 8 — exactly the `bea_official` set (AR, CA, DC, HI, IA, MS,
  NJ, OK).
- **Refused:** 43 — exactly the `estimate` set (AL, AK, AZ, CO, CT, DE, FL,
  GA, ID, IL, IN, KS, KY, LA, ME, MD, MA, MI, MN, MO, MT, NE, NV, NH, NM, NY,
  NC, ND, OH, OR, PA, RI, SC, SD, TN, TX, UT, VT, VA, WA, WV, WI, WY).

All refusal messages carry the canonical pattern
`"Regional price parity for '<state_name>' is currently an estimate
(data_source=estimate) and strict mode is enabled."` — satisfying acceptance
criterion "structured null with a helpful error message, never raises."

### `compare_purchasing_power`: arithmetic reproduction (7/7)

For each of the 7 success cases, recomputing
`round(salary * ppm, 2)` off the Gold row reproduces every value in the
eval's `expected_output.data` / `verification_key`:

| case_id | salary | adjusted_a (CA) | adjusted_b (IA) | difference | difference_pct | Match |
|---------|-------:|-----------------:|-----------------:|-----------:|---------------:|-------|
| `compare-ca-ia-30000` | 30000 | 27100.27 | 34168.56 | 7068.29 | 26.08 | OK |
| `compare-ca-ia-50000` | 50000 | 45167.12 | 56947.61 | 11780.49 | 26.08 | OK |
| `compare-ca-ia-65000` | 65000 | 58717.25 | 74031.89 | 15314.64 | 26.08 | OK |
| `compare-ca-ia-75000` | 75000 | 67750.68 | 85421.41 | 17670.73 | 26.08 | OK |
| `compare-ca-ia-100000` | 100000 | 90334.24 | 113895.22 | 23560.98 | 26.08 | OK |
| `compare-names-65k` | 65000 | 58717.25 | 74031.89 | — | — | OK (via verification_key) |
| `compare-fips-65k` | 65000 | 58717.25 | 74031.89 | — | — | OK (via verification_key) |

The canonical $65K example from the spec (`CA → $58,717.25 vs IA → $74,031.89`)
reproduces exactly, confirming the MCP handler's
`round(salary * purchasing_power_multiplier, 2)` formula and Python's
banker's-rounding semantics. Note that `difference_pct = 26.08` is stable
across all five salary levels because the ratio `ppm_b / ppm_a - 1` is
invariant under multiplication by salary.

---

## Live Tool Runs — All 65 Eval Cases

Every one of the 65 eval cases was executed against the live MCP server
(`FutureProofMCPServer._handle_get_regional_price_parity` and
`_handle_compare_purchasing_power`) with the Iceberg warehouse at
`data/catalog/catalog.db`. Each case's `verification_key` (dotted-path
equalities plus `message_contains` substring checks) was evaluated against the
actual response.

**Result: 65/65 PASS. 0 failures. 0 exceptions raised.**

---

## Untested Input Shapes (Defense-in-Depth Edges)

These are edges the live server already handles correctly but the eval set
does not enumerate. None are required by the spec's 11 categories; they are
documented so @dq-rule-writer and the test suite can decide whether to add
explicit coverage.

### `get_regional_price_parity`

| Input | Live behavior | Covered in eval? |
|---|---|---|
| `{"state": None}` | null + "Unknown state: None" | no |
| `{"state": 6}` (int) | null + "Unknown state: 6" | no |
| `{"state": 6.0}` (float) | null + "Unknown state: 6.0" | no |
| `{"state": "6"}` (FIPS without leading zero) | null + "Unknown state: '6'" | no |
| `{"state": "00"}`, `"03"`, `"99"` (invalid FIPS) | null + Unknown state | no |
| `{"state": True}` | null + "Unknown state: True" | no |
| `{"state": ["CA"]}` (list) | null + "Unknown state: ['CA']" | no |
| `{}` (missing `state` key) | null + "Unknown state: None" | no |
| `{"state": "CA  "}` / `"  CA"` / `"Ca"` | success (trim + case-fold) | indirectly (`caseins-california-23`) |
| `{"state": "\tCalifornia\t"}` (tab whitespace) | success | no (eval only tests space whitespace) |
| `{"state": "district of columbia"}` | success | no (DC not in case-insensitive set) |
| `{"state": "TX", "verified_only": "true"}` (str) | refused as strict (Python truthiness via `bool()`) | no |
| `{"state": "TX", "verified_only": None}` (None) | non-strict success (None → False) | no |

### `compare_purchasing_power`

| Input | Live behavior | Covered in eval? |
|---|---|---|
| missing `salary` key | null + salary validation msg | no |
| missing `state_a` or `state_b` | null + Unknown state | no |
| `salary = NaN` | null + salary validation | no |
| `salary = inf` / `-inf` | null + salary validation | no |
| `salary = False` (bool) | null + salary validation | no (eval only tests `True`) |
| `salary = 0.01` (tiny positive) | success | no |
| `salary = 9_999_999.99` (just under max) | success | no |
| same-state via whitespace (`CA` vs `  CA  `) | null + same-state | no (eval covers usps/name/fips equivalence but not whitespace) |
| b-estimate first under strict (CA vs NY) | null + "New York is currently an estimate" | no (eval only refuses from state_a side) |
| both states estimate under strict (TX vs NY) | null identifying first offender (TX) | no |

### Recommendations for @dq-rule-writer

These are the defense-in-depth edge cases most worth promoting to explicit
eval or DQ coverage:

1. **Float FIPS coercion** (`6.0`, `6`). The spec says FIPS is a 2-digit
   string — adding one negative eval case documents that the tool does not
   accept numeric FIPS.
2. **NaN / inf salary.** `_validate_salary` explicitly guards against these,
   but there is no eval case that pins the behavior. A single case would
   protect against future regressions.
3. **`salary = False`.** The eval covers `True` but not `False`. Bool
   handling is exactly the bug Python's `isinstance(False, int) == True`
   invites.
4. **Same-state via whitespace** (`CA` vs `  CA  `). The eval covers
   usps/name/fips equivalence after normalization but not
   whitespace-trimmed equivalence.
5. **Strict mode, offender in state_b position** (`CA` vs `NY` with
   `verified_only=true`). All four eval cases put the offending state in
   `state_a`, `state_b` when one side is estimated, or both. There is no
   case where state_a is verified and state_b is the estimate — the current
   implementation handles it correctly (`offenders[0]` picks the first
   estimate encountered in `(row_a, row_b)` order) but the eval does not pin
   the guarantee.
6. **Tab / non-space whitespace in full name** (`\tCalifornia\t`). The eval's
   whitespace case uses spaces only.

None of these are blockers. All current eval cases pass and all 11 spec
categories are met at or above the minimum.

---

## Anomalies

None. All of the following were verified as correct:

- No raised exceptions across 65 eval cases + 19 ad-hoc edge probes on
  `get_regional_price_parity` + 13 on `compare_purchasing_power`.
- No byte-for-byte mismatches between the eval's verified-state payloads and
  the Gold rows.
- No arithmetic discrepancies in `compare_purchasing_power` success cases.
- No state in the 51-state set escapes strict mode (exhaustive 51-row sweep:
  8 bea_official → succeed, 43 estimate → refuse, 0 others).

---

## Governance

- Every response carries `governance.table = "consumable.regional_price_parities"`
  via `BaseMCPServer.attach_governance` / `enrich_response`. The richer
  `quality_tier` and `owner` fields mentioned in the spec example are
  framework-controlled and depend on the `BaseMCPServer` subclass
  configuration — they are not asserted by any eval case, which is
  appropriate (framework concern, not tool concern).

---

## Files Referenced

- **Spec:** `/Users/jcernauske/code/bright/futureproof-data/docs/specs/mcp-bea-rpp.md`
- **Eval set:** `/Users/jcernauske/code/bright/futureproof-data/data/ai_ready/eval/mcp-bea-rpp-eval.jsonl`
- **MCP server:** `/Users/jcernauske/code/bright/futureproof-data/src/mcp_server/futureproof_server.py`
- **State normalizer:** `/Users/jcernauske/code/bright/futureproof-data/src/mcp_server/_state_input.py`
- **Gold parquet:** `/Users/jcernauske/code/bright/futureproof-data/data/gold/iceberg_warehouse/consumable/regional_price_parities/data/00000-0-07edfd60-dda9-4d71-936a-0ea5bdb54bb6.parquet`
- **Gold EDA (parent):** `/Users/jcernauske/code/bright/futureproof-data/governance/eda/gold-regional-price-parities-eda.md`
