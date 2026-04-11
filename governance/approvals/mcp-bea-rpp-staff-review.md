## Staff Engineer Review: mcp-bea-rpp

**Review Type:** Final Sign-Off
**Reviewer:** @staff-engineer
**Date:** 2026-04-11
**Status:** APPROVED

---

### Verdict

Production quality. I will put my name on this. This is what a thin MCP
layer over a well-governed Gold table is supposed to look like: two
handlers, a pure-function normalizer, an override to patch a framework
governance gap, and no cleverness anywhere. The spec is implemented to
the letter, Bronze Condition 7 is fully discharged end-to-end across all
four zones, and every number in the spec's arithmetic example reproduces
bit-exact against the live server and the Gold golden dataset. **APPROVED.
Flip `governance/data-contracts/mcp-bea-rpp.yaml` from `draft` to `active`.**

---

### Code Quality

**`src/mcp_server/futureproof_server.py`** — clean.

- Both new tools registered alongside `get_ai_exposure` following the
  established pattern. No copy-paste rot; the `ToolDef` descriptions
  are specific enough that a Gemma client has everything it needs
  (input forms, strict-mode semantics, what `data_source` means).
- `_fetch_rpp_row`, `_rpp_row_to_payload`, `_compact_side`,
  `_validate_salary` are small single-purpose functions with names
  that describe what they do. No god methods.
- `_validate_salary` explicitly rejects `bool` before the `isinstance`
  check (Python's `True` is an `int` subclass and would otherwise
  silently become `$1`), and rejects NaN / inf. That is careful work
  and I would have flagged its absence.
- The `attach_governance` override is the load-bearing piece. It
  reads the project's top-level-YAML contract format directly,
  caches parsed results at class level, degrades gracefully on
  missing/unparseable contracts with a `logger.warning` (not a
  swallowed exception), and extracts the canonical tier token from
  a folded scalar. The comment above it cites the exact DQ rule
  (MCP-BEA-002) and the acceptance criterion line number in the
  spec — that is the right kind of comment: WHY, not WHAT.
- No abstraction astronautics. Two handlers, two helper methods per
  handler, one shared `_fetch_rpp_row`. Done.

**`src/mcp_server/_state_input.py`** — clean.

- `USPS_TO_FIPS` and `STATE_NAME_TO_FIPS` are *derived* from the
  canonical Silver dict (`FIPS_TO_USPS`), not duplicated. That is
  exactly what the pre-review asked for and prevents drift.
- `FIPS_TO_STATE_NAME` is hand-listed but guarded by a `_self_check()`
  that runs at import time and verifies bidirectional completeness
  against `FIPS_TO_USPS`. If someone ever edits one dict without the
  other, the module fails to import — which is the correct failure
  mode for a closed enumeration.
- `normalize_state_input` is a pure function, never raises, rejects
  non-strings and empty strings with `None` (not exceptions).
- Case-insensitivity is handled at the single chokepoint, not
  sprayed across the handlers.

**What I didn't find:** god functions, swallowed exceptions, tests
asserting on `len > 0`, magic numbers without named constants
(`MAX_SALARY`), hand-rolled FIPS tables, mutable default arguments,
or comments explaining what obvious code does.

Ruff is clean on `src/mcp_server/`.

---

### Test Quality

**Real tests, not theater.**

- 99/99 mcp-bea-rpp tests pass (46 in `test_get_regional_price_parity.py`
  + 30 in `test_compare_purchasing_power.py` + 23 in shared state-input
  tests). MCP minimum is 10; this delivers **nearly 10x the floor**.
- `VERIFIED_ROWS` fixture uses the **exact** Gold values from
  `governance/golden-datasets/gold-regional-price-parities-golden.json`
  — 8 BEA-verified states with full-precision `purchasing_power_multiplier`
  anchored to `100.0 / rpp_all_items` at IEEE-754 double precision. The
  adjusted_Nk columns are pre-computed values, not `assert > 0` nonsense.
- Strict-mode tests assert both the positive path (8 verified states
  pass) and the refusal path (sample estimate states return null with
  'strict' in the message). Not just "no exception raised."
- The `compare_purchasing_power` test for CA vs IA at $65K asserts the
  exact numbers from the spec ($58,717.25 / $74,031.89 / $15,314.64
  / 26.08%) — not a tolerance of "within 5%."
- Input normalization tests cover all three forms plus case-insensitivity,
  whitespace, unknown strings, non-strings, and the empty-string edge.
- Every assertion I spot-checked is on a specific expected value, not
  on the absence of error. Zero `assert True` found.

The 65-case eval set against the live server is the second line of
defense and it also passes 65/65. Eval keys use full-precision `ppm`
values, matching pre-review Advisory #1 resolution.

---

### Spec Compliance

Every one of the 9 acceptance criteria (docs/specs/mcp-bea-rpp.md
lines 229-238) was independently verified by live probe against the
actual Iceberg-backed server, not just by the test suite:

| # | Criterion | Staff Verification |
|---|-----------|---------------------|
| 1 | Both tools registered in `FutureProofMCPServer.get_tools()` | PASS — verified by introspection |
| 2 | Input normalization FIPS/USPS/full-name, case insensitive | PASS — probed `CA`, `California`, `california`, `06` all return state_fips=06 |
| 3 | 8 BEA-verified states return correct cost_tier + adjusted_Nk | PASS — all 8 match golden dataset exactly (table below) |
| 4 | Strict mode refuses 43 estimated states | PASS — full 51-FIPS sweep: 43/43 refused |
| 5 | Strict mode returns 8 verified states successfully | PASS — full sweep: {AR, CA, DC, HI, IA, MS, NJ, OK} all pass |
| 6 | CA vs IA @ $65K = (58717.25 / 74031.89 / 15314.64 / 26.08) | PASS — bit-exact live probe |
| 7 | Unknown state returns null, never raises | PASS — probed 'Xanadu', got structured null; 0 exceptions across 65 eval cases |
| 8 | Eval ≥ 50 cases, all passing against live server | PASS — 65/65 (30% above floor) |
| 9 | `governance.quality_tier == 'partial_verification'` on every response | PASS (post-remediation) — verified on success **and** null responses |

---

### Data Correctness Spot-Check (MANDATORY)

Live probe against the actual `consumable.regional_price_parities`
Iceberg table via the MCP server, compared against
`governance/golden-datasets/gold-regional-price-parities-golden.json`
which itself cites BEA Regional Economic Accounts SARPP LineCode=1
2024 vintage:

| Entity | Metric | Period | Pipeline Value | Reference Value | Source | Match? |
|--------|--------|--------|---------------|-----------------|--------|--------|
| California (06) | rpp_all_items | 2024 | 110.7 | 110.7 | golden-dataset + BEA SARPP | EXACT |
| California (06) | adjusted_50k | 2024 | 45167.12 | 45167.12 | golden-dataset | EXACT |
| California (06) | ppm | 2024 | 0.9033423667570009 | 0.9033423667570... | 100.0/110.7 IEEE-754 | EXACT |
| Hawaii (15) | adjusted_50k | 2024 | 45454.55 | 45454.55 | golden-dataset | EXACT |
| DC (11) | adjusted_50k | 2024 | 45495.91 | 45495.91 | golden-dataset | EXACT |
| New Jersey (34) | adjusted_50k | 2024 | 45955.88 | 45955.88 | golden-dataset | EXACT |
| Arkansas (05) | adjusted_50k | 2024 | 57537.40 | 57537.40 | golden-dataset | EXACT |
| Mississippi (28) | adjusted_50k | 2024 | 57471.26 | 57471.26 | golden-dataset | EXACT |
| Iowa (19) | adjusted_50k | 2024 | 56947.61 | 56947.61 | golden-dataset | EXACT |
| Oklahoma (40) | adjusted_50k | 2024 | 56947.61 | 56947.61 | golden-dataset | EXACT |
| compare(CA,IA,65K) | state_a.adjusted_salary | 2024 | 58717.25 | 58717.25 | spec §example | EXACT |
| compare(CA,IA,65K) | state_b.adjusted_salary | 2024 | 74031.89 | 74031.89 | spec §example | EXACT |
| compare(CA,IA,65K) | difference | 2024 | 15314.64 | 15314.64 | spec §example | EXACT |
| compare(CA,IA,65K) | difference_pct | 2024 | 26.08 | 26.08 | spec §example | EXACT |

**14/14 exact matches.** Zero tolerance drift. Iowa/Oklahoma tie at
rpp=87.8 is a legitimate data coincidence documented in the golden
dataset (`tie_note`), not a bug.

The MCP layer applies no transformations, so it correctly inherits
Gold's data quality guarantees without introducing any. The golden
dataset was produced by @data-analyst during the Gold spec and is
referenced unchanged here. This satisfies the reference-data requirement
that exists because I once approved a $20B revenue value that should
have been $65B. Not today.

---

### Bronze Condition 7 — Final Closure

Bronze staff-review Condition 7 required that the MCP tool surface
`verification_status` as `data_source` on every response and expose a
strict mode that refuses estimate rows. Both are implemented:

- **Surfacing:** `_rpp_row_to_payload` line 430 and `_compact_side`
  line 551 rename the field on egress. Live probe: every one of 51
  FIPS codes returns `data_source` ∈ {`bea_official`, `estimate`}.
- **Strict mode:** 43/43 estimate states refused with 'strict' in the
  message, 8/8 verified states pass through. Full 51-state sweep
  performed independently by this review, zero cross-contamination.

The Gold contract's `condition_7_carry_forward_to_mcp` block was
flipped from `FORWARD-ONLY OBLIGATION` to `DISCHARGED` during the
post-review at
`governance/data-contracts/consumable-regional-price-parities.yaml:565`.
I verified the flip is present and the back-reference to this post-
review is real, not a placeholder.

**Bronze → Silver → Gold → MCP BEA RPP chain is closed. Condition 7 is
fully discharged across all four zones.**

---

### Governance Artifacts

Not boilerplate. Everything references real data:

- `governance/dq-rules/mcp-bea-rpp.json` — 350 lines, 16 interface-
  contract rules (14 P0, 2 P1). Not a copy of the Gold rules — these
  cover wire-level invariants the Gold SQL rules cannot see
  (field renaming, governance dict shape, null-case structure,
  strict-mode refusal, arithmetic reconstruction).
- `governance/dq-results/mcp-bea-rpp-20260411T050916Z.json` — 16/16
  PASS, P0 gate clean, post-remediation results retained alongside
  the pre-remediation 15/16 run for audit.
- `governance/lineage/mcp-bea-rpp-20260411.json` — 578 lines, 33
  column mappings across two tools, brightsmith facet block with
  agent attribution and Condition 7 annotation.
- `governance/data-contracts/mcp-bea-rpp.yaml` — 988 lines, covers
  both tools, 24 CDE / 0 PII (inherited from Gold, zero new flags),
  10 business terms (BT-098 through BT-107) all resolved in the
  glossary, dedicated `bronze_condition_7` section. Currently `draft`
  — to be flipped to `active` on this approval.
- `governance/dq-scorecards/mcp-bea-rpp-scorecard.md` — real
  execution results with remediation appendix.
- `data/ai_ready/eval/mcp-bea-rpp-eval.jsonl` — 65 cases covering all
  11 required categories in spec §"Eval Set".

---

### Issues

| # | Severity | File | Issue | Required Fix |
|---|----------|------|-------|-------------|
| — | — | — | None. | — |

No CHANGES REQUIRED. No REJECTED items. No ADVISORIES.

---

### Open Items (non-blocking, for framework follow-up)

These are context for the framework team, not blockers for this spec:

1. **`attach_governance` contract cache is class-level dict.** Fine for
   this spec (server process is long-lived and the contract file is
   read-once), but if contract hot-reload is ever added, switch to
   `lru_cache` with a TTL or an explicit invalidation entry point.
2. **`_extract_quality_tier_token` splits on `-`.** Latent truncation
   risk if a hypothetical new canonical tier ever contains a hyphen
   (e.g., `high-assurance`). None of the current tier tokens do, so
   this is latent not live. File a framework follow-up to enum-check
   tier values against a fixed allow-list when the contract loader
   supports it.
3. **`brightsmith.infra.contract verify mcp-bea-rpp` fails with
   `Empty namespace identifier`.** Pre-existing framework limitation
   for MCP-layer contracts that don't map to an Iceberg namespace;
   affects peer `mcp-ai-exposure` the same way. Not an mcp-bea-rpp
   defect. Framework-level fix.

None of these three rise to the level of a changes-required gate.
They are each one-line notes for a future framework sprint.

---

### Pipeline Gate Note

`pipeline_gate validate` reports the DQ scorecard was modified after
@dq-engineer's completion (expected — @governance-reviewer updated it
during post-review with the remediation appendix) and that
@staff-engineer is NOT_STARTED (this review closes that). Both are
expected; neither is a defect. The post-review artifact modification
is documented and appropriate.

---

### Refresh Blockers (carried forward from Bronze)

Acknowledging, not gating:

- 43/51 state RPP values remain estimates, not BEA-authoritative.
- Live BEA API has never been exercised — all values trace to a
  static CSV snapshot whose sha256 integrity is not captured.
- When the refresh lands and the allow-list flips to all 51, strict
  mode will return 51 rows instead of 8 and the post-refresh test
  suite will need to assert on the new `BEA_VERIFIED_FIPS` count.

These are Bronze-era obligations pinned to the `raw-ingest-bea-rpp`
refresh story. They do not block MCP sign-off because the MCP tool
correctly propagates whatever provenance Gold carries. If Gold flips
to 51 verified rows, the strict-mode refusal count at this layer
drops to 0 — that is by design.

---

### What's Acceptable

Fine. Ship it. The arithmetic is exact, the strict mode works, the
null-case messages are helpful without being chatty, the governance
override is defensive, the tests assert on specific values, the
golden dataset is real, and Bronze Condition 7 is now fully closed
end-to-end. This is the second time @mcp-engineer and @primary-agent
have delivered a thin MCP layer that passes staff review on the first
submission; the pattern works.

The post-review also caught the `attach_governance` framework gap,
forced a clean remediation, re-executed all 16 DQ rules, and updated
the Gold contract's Condition 7 status. That is exactly what a post-
review is supposed to do and I appreciate the DQ-engineer escalation
on MCP-BEA-002 — it is the right kind of check to have caught.

---

### Final Decision

**APPROVED.** Proceeding with:

1. Flip `governance/data-contracts/mcp-bea-rpp.yaml` line 29
   `status: draft` → `status: active`.
2. Mark the `mcp-bea-rpp` spec pipeline step `staff-engineer` as
   `COMPLETED`.

BEA RPP Bronze → Silver → Gold → MCP chain is now end-to-end complete.
Bronze Condition 7 is fully discharged.

— @staff-engineer
