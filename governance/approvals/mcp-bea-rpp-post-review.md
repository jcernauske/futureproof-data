## Governance Review: mcp-bea-rpp
**Review Type:** Post-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-11
**Verdict:** APPROVED

---

### Scope Recap

`mcp-bea-rpp` exposes two read-only MCP tools — `get_regional_price_parity`
and `compare_purchasing_power` — over `consumable.regional_price_parities`
(51 rows, Gold contract ACTIVE, `partial_verification` tier). No new data,
no transformations, no schema changes; a thin wire layer plus a pure-Python
state normalizer. This spec closes the MCP half of Bronze staff-review
Condition 7, completing the Bronze → Silver → Gold → MCP chain for BEA RPP
provenance end to end.

The pre-review raised two advisories:

1. **Full-precision `purchasing_power_multiplier`** — resolved by returning
   the raw Gold double unchanged on the wire (verified below).
2. **Eval file extension mismatch vs `mcp-ai-exposure-eval.json`** —
   informational; no action required.

The pipeline execution hit one P0 failure during @dq-engineer's run
(MCP-BEA-002: `governance.quality_tier` was absent on every response
because the framework's `BaseMCPServer.attach_governance` does not emit it).
The primary agent remediated by overriding `attach_governance` on
`FutureProofMCPServer`. This post-review re-executed all 16 rules against
the remediated server — 16/16 pass.

---

### Post-Implementation Checklist

| # | Item | Status |
|---|------|--------|
| 1 | Lineage | PASS — `governance/lineage/mcp-bea-rpp-20260411.json`: 2 COMPLETE events, 14 + 19 = 33 column mappings, brightsmith facet block includes agent attribution, runtime metrics, and Bronze Condition 7 annotation |
| 2 | DQ Rules | PASS — `governance/dq-rules/mcp-bea-rpp.json`: 16 interface-contract rules (14 P0, 2 P1) authored by @dq-rule-writer; covers MCP-layer wire invariants that Gold SQL rules cannot see |
| 3 | DQ Execution | PASS — executed twice: pre-remediation `governance/dq-results/mcp-bea-rpp-20260411T042033Z.json` (15/16), post-remediation `governance/dq-results/mcp-bea-rpp-20260411T050916Z.json` (16/16); both retained for audit |
| 4 | DQ P0 Gate | PASS — post-remediation P0 gate: PASS (zero P0 failures). Pre-remediation failure MCP-BEA-002 is documented, fixed, and re-verified |
| 5 | DQ Scorecard | PASS — `governance/dq-scorecards/mcp-bea-rpp-scorecard.md` updated with remediation appendix + post-remediation summary. Scorecard derived from real execution results, not test-based |
| 6 | CDE/PII Tags | PASS — 24 CDE / 0 PII across 33 wire response fields in `governance/data-contracts/mcp-bea-rpp.yaml` (matches @cde-tagger report). Zero new PII, zero new CDE flags at the MCP layer — all flags propagate from the Gold contract |
| 7 | Data Dictionary | PASS — `governance/data-dictionary.json` has top-level entries `tables.mcp.get_regional_price_parity` and `tables.mcp.compare_purchasing_power` with full column trees including `spec_reference`, `data_contract`, `backing_table`, and per-leaf descriptions |
| 8 | Data Contracts | PASS — `governance/data-contracts/mcp-bea-rpp.yaml` (988 lines, DRAFT, quality_tier `partial_verification`) covers both tools, references all 10 business terms (BT-098 through BT-107, all verified present in glossary), includes a dedicated `bronze_condition_7` section pinning closure evidence to MCP-BEA rule IDs |
| 9 | Audit Trail | PASS — 6 mcp-bea-rpp audit logs in `governance/audit-trail/`: data-analyst, doc-generator, dq-engineer, dq-rule-writer, lineage-tracker, cde-tagging. Data-steward N/A per pipeline summary (no glossary changes — all 10 BT entries were added on the Gold spec, not here) |
| 10 | Schema Changes | N/A — MCP zone adds no Iceberg DML. Wire-level response schemas match spec §"Success response" byte-for-byte (verified by live probe) |
| 11 | Data Models (Base/Consumable only) | N/A — MCP zone skips the 3-stage data modeling progression; Gold already has approved physical/logical/conceptual models |
| 12 | No Orphaned Artifacts | PASS — every field referenced in DQ rules, lineage, contract, and data dictionary resolves to a real response field on the live server; zero phantom BT IDs |
| 13 | Consistency | PASS — lineage columnLineage field names, CDE-tagging report field names, data contract response schema field names, and data dictionary field names all agree (33 fields in each) |
| 14 | Insight Traceability | N/A — no insight report exists for the MCP zone transition; the two insight reports in `governance/insights/` are silver-to-gold scoped |

---

### Acceptance Criteria Verification

All 9 spec acceptance criteria (docs/specs/mcp-bea-rpp.md lines 229-238) verified by live probe against `FutureProofMCPServer`:

| # | Criterion | Verification |
|---|-----------|-------------|
| 1 | Both tools registered in `FutureProofMCPServer.get_tools()` | PASS — `src/mcp_server/futureproof_server.py:73-194` registers both tools, following the `get_ai_exposure` pattern exactly |
| 2 | Input normalization handles FIPS / USPS / full name, case-insensitive | PASS — `src/mcp_server/_state_input.py` with import-time self-check against Silver canonical module; 5/5 case-insensitive eval cases pass |
| 3 | All 8 BEA-verified states return correct cost_tier + adjusted_Nk matching Gold spot-check | PASS — 8/8 `verified-*` eval cases pass; MCP-BEA-005 reconstructs `round(N × ppm, 2) == adjusted_Nk` exactly for all 8 rows at all 4 salary levels |
| 4 | Strict mode refuses all 43 estimated states with structured null response | PASS — live sweep of all 51 FIPS codes via `verified_only=true`: 43 refused with 'strict' in message, 8 succeeded with `bea_official` |
| 5 | Strict mode returns all 8 verified states successfully | PASS — live sweep: 8/8 verified states returned non-null data with `data_source='bea_official'` under `verified_only=true` |
| 6 | `compare_purchasing_power` CA vs IA at $65K returns exactly ($58,717.25 / $74,031.89 / $15,314.64 / 26.08) | PASS — live probe: `adjusted_a=58717.25, adjusted_b=74031.89, diff=15314.64, diff_pct=26.08` (exact). MCP-BEA-013 verifies reproduction across all 3 input forms (USPS, full name, FIPS) |
| 7 | Unknown state returns null with helpful error, never raises | PASS — 7/7 unknown-* and compare-unknown-* eval cases return structured null with non-empty message; zero exceptions across 65 eval cases |
| 8 | Eval set has ≥ 50 cases, all passing against the live MCP server | PASS — 65 cases in `data/ai_ready/eval/mcp-bea-rpp-eval.jsonl`, 65/65 pass (30% above minimum) |
| 9 | `governance.quality_tier` attached to every response is `partial_verification` | PASS (post-remediation) — 65/65 responses across both tools carry `governance.quality_tier == 'partial_verification'` and `governance.owner == '@doc-generator'` after the `attach_governance` override landed at `src/mcp_server/futureproof_server.py:305-334` |

Test suite: **99/99 mcp-bea-rpp tests pass** (`uv run pytest tests/mcp/test_get_regional_price_parity.py tests/mcp/test_compare_purchasing_power.py -q`). The MCP minimum is 10; this spec delivers 99 — nearly 10x the floor. Ruff clean on `src/mcp_server/`.

---

### Pre-Review Advisories Resolution

#### Advisory #1 — Full-precision `purchasing_power_multiplier`

**Resolved.** Live probe shows `CA` returns `"purchasing_power_multiplier": 0.9033423667570009` (full IEEE-754 double, matching Silver's `100.0 / 110.7`). This is sufficient for `round(65000 * ppm, 2) == 58717.25` to reproduce exactly client-side. The handler comment at `_rpp_row_to_payload` (lines 405-415) explicitly cites the advisory: *"Preserves full-precision `purchasing_power_multiplier` (pre-review Advisory #1 — the caller must be able to reconstruct arithmetic exactly)."* MCP-BEA-005 pins this invariant across all 8 BEA rows for all 4 salary levels. Zero ambiguity between the displayed ppm and the adjusted values.

#### Advisory #2 — Eval file extension mismatch

No action required; the JSONL format is strictly better than the prior JSON-array format for mcp-ai-exposure. Cleanup of the peer eval file is out of scope for this spec and should be tracked separately.

---

### Bronze Condition 7 (MCP half) — Closure Verification

Condition 7 required two things of the MCP layer, per `governance/approvals/raw-ingest-bea-rpp-staff-review.md`:

**Requirement (a): Per-row `verification_status` surfaced as `data_source` on every response.**

- **Tool 1:** `_rpp_row_to_payload` at `src/mcp_server/futureproof_server.py:405-432` renames `verification_status` → `data_source`. Live probe: CA returns `"data_source": "bea_official"`; HI returns `"data_source": "bea_official"`; MS returns `"data_source": "bea_official"`.
- **Tool 2:** `_compact_side` at `src/mcp_server/futureproof_server.py:538-552` renames `verification_status` → `data_source` on each side. Live probe: `compare(CA, IA)` returns both sides with `data_source == "bea_official"`.
- **DQ coverage:** MCP-BEA-001 (enum membership), MCP-BEA-003 (8-state FIPS allow-list equality). Both pass on 16/16 anchor cases.
- **Eval coverage:** all 8 `verified-*` cases + 8 `estimate-*` cases + all 8 `strict-ok-*` cases carry the field.

**Requirement (b): `verified_only=true` strict mode refuses `estimate` rows with structured null.**

- **Tool 1:** `src/mcp_server/futureproof_server.py:477-489` — returns structured null with message containing 'strict' and the state name when the row is an estimate. Live probe sweep of all 51 FIPS: **43/43 estimate states refused, 8/8 verified states pass**. Zero cross-contamination.
- **Tool 2:** `src/mcp_server/futureproof_server.py:643-661` — refuses when EITHER state is an estimate, with message identifying the offender and containing 'Strict mode'. MCP-BEA-009 covers offender in position a, position b, and both sides.
- **DQ coverage:** MCP-BEA-007 (8/8 pass), MCP-BEA-008 (5/5 refuse), MCP-BEA-009 (4/4 compare refusals). All pass.
- **Eval coverage:** 8 `strict-ok-*` + 5 `strict-refuse-*` + 4 `compare-strict-refuse-*` cases.

**Gold contract obligation discharged:** `governance/data-contracts/consumable-regional-price-parities.yaml` §`staff_review_conditions.condition_7_carry_forward_to_mcp` has been updated from `FORWARD-ONLY OBLIGATION` → `DISCHARGED` with a reference back to this post-review. The forward-only obligation documented at the Gold contract is now fully closed across the Bronze → Silver → Gold → MCP chain.

**Verdict on Condition 7:** **FULLY CLOSED end-to-end.** No daylight between the Bronze staff-review requirement, the Gold contract forward-only note, the MCP spec acceptance criteria, the 16 MCP-BEA DQ rules, the 65 eval cases, the 99-test pytest suite, and the live server behavior.

---

### Cross-Agent Consistency

| Artifact pair | Consistency check |
|---|---|
| lineage `columnLineage` ↔ contract `response_schema` | 33 fields on each side; field names agree (verified path-by-path) |
| CDE-tagging report ↔ contract CDE flags | 24 CDE / 0 PII on both sides |
| data dictionary field paths ↔ contract field paths | `tables.mcp.get_regional_price_parity.columns` + `tables.mcp.compare_purchasing_power.columns` cover the same field set |
| contract `business_terms_referenced` ↔ `governance/business-glossary.json` | 10/10 BT IDs (BT-098 through BT-107) resolve; zero phantom |
| DQ rules `tool` field ↔ registered tools | Both tools named in rules match `FutureProofMCPServer.get_tools()` names |
| spec example arithmetic ↔ live server output | exact match: (58717.25, 74031.89, 15314.64, 26.08) |

---

### Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| — | — | None. All pre-review advisories resolved. MCP-BEA-002 P0 failure remediated, re-executed, and verified. Gold contract's Condition 7 carry-forward status updated to DISCHARGED. | None |

No CHANGES REQUESTED. No REJECTED items.

---

### Decision Rationale

This spec is a textbook thin MCP layer — a read-only tool surface over a well-governed Gold table with no new data, no new transformations, and no new governance surface beyond what Gold already enforces. The entire spec is executable as "rename verification_status, bundle adjusted_Nk into a struct, register two tools, cover with tests + eval + interface-contract DQ."

**What went well:**

- **Pre-review forward-looking checklist was highly effective.** Every item on the forward-looking post-review checklist (pre-review lines 192-208) was either verified PASS or explicitly N/A. Advisory #1 (full-precision ppm) was resolved exactly as recommended.
- **Bronze Condition 7 is now fully closed with zero daylight across the four zones.** The Gold contract's `FORWARD-ONLY OBLIGATION` marker was the last hint of an unclosed loop; this post-review updated it to `DISCHARGED` with a back-reference to this file. The audit trail is intact: Bronze staff review → Gold contract documents forward obligation → MCP spec implements → MCP contract discharges → Gold contract updated.
- **DQ re-execution caught the framework gap and forced the right fix.** MCP-BEA-002 is exactly the kind of contract drift that eval sets alone cannot catch (governance metadata is framework-controlled, not eval-assertable by default). The DQ engineer's escalation forced the primary agent to override `attach_governance` cleanly and defensively (gracefully degrades if the contract file is missing or malformed, caches the parsed YAML, extracts just the canonical tier token from a folded scalar). This is the right architectural seam.
- **Zero phantom BT IDs, zero field-name drift, zero orphaned artifacts.** Every cross-check between lineage, contract, dictionary, DQ rules, and the live server passes. The 10 business terms (BT-098 through BT-107) all resolve in `governance/business-glossary.json`.
- **Live probe is exact.** Every number in the spec's `compare_purchasing_power` example reproduces bit-exact: 58717.25, 74031.89, 15314.64, 26.08. The full 51-state strict-mode sweep returns the canonical 43:8 partition with zero false negatives and zero false positives.

**Minor observations for staff-engineer consideration (not blocking):**

1. The `attach_governance` override reads the contract YAML on every call and caches by table name. The cache is a class-level dict, so across-instance state persists; this is fine for a long-running server process but would benefit from an explicit `lru_cache` decorator or a TTL if the contract is ever hot-reloaded. For this spec, not a concern.
2. The `_extract_quality_tier_token` helper splits on any of `\n`, space, em-dash, or hyphen. For tiers that contain a hyphen in their canonical name (e.g., a hypothetical `high-assurance`), the helper would truncate. None of the current canonical tier names contain a hyphen, so this is latent not live; a lint rule or enum-check could catch it if a new tier lands.
3. The contract verify CLI (`brightsmith.infra.contract verify mcp-bea-rpp`) fails with `table_load: Empty namespace identifier` — the same mode as the peer `mcp-ai-exposure` and `consumable-regional-price-parities` contracts. This is a framework/tooling limitation for contracts that don't point at a directly-loadable Iceberg namespace in the expected shape; not an mcp-bea-rpp defect.

None of these rise to ADVISORY — they are context for staff-engineer to decide whether to file framework follow-ups.

**Post-review verdict: APPROVED for staff-engineer sign-off.**

The spec is implementation-complete, governance-complete, and Bronze Condition 7 is fully closed end-to-end across the Bronze → Silver → Gold → MCP chain. The DQ scorecard has been updated to reflect 16/16 rules passing post-remediation, the Gold contract's Condition 7 carry-forward status has been flipped to DISCHARGED, and both live-probe verification and the 65-case eval set confirm the spec's arithmetic, strict-mode, and provenance guarantees against the live MCP server.

---

### Audit Trail Entry

- **Reviewed:** mcp-bea-rpp (post-implementation)
- **Artifacts verified:** docs/specs/mcp-bea-rpp.md; src/mcp_server/futureproof_server.py; src/mcp_server/_state_input.py; governance/dq-rules/mcp-bea-rpp.json; governance/dq-results/mcp-bea-rpp-20260411T042033Z.json; governance/dq-results/mcp-bea-rpp-20260411T050916Z.json (created by this review); governance/dq-scorecards/mcp-bea-rpp-scorecard.md (updated by this review); governance/lineage/mcp-bea-rpp-20260411.json; governance/data-contracts/mcp-bea-rpp.yaml; governance/data-contracts/consumable-regional-price-parities.yaml (updated by this review — Condition 7 status); governance/data-dictionary.json; governance/business-glossary.json; governance/audit-trail/2026-04-11-*-mcp-bea-rpp.md; data/ai_ready/eval/mcp-bea-rpp-eval.jsonl; tests/mcp/test_get_regional_price_parity.py; tests/mcp/test_compare_purchasing_power.py
- **Checks run:** 65-case eval set via live server (65/65 PASS); 16-rule DQ re-execution via live server (16/16 PASS, P0 gate PASS); 99-test pytest suite (99/99 PASS); live probes for CA/TX/HI/MS + compare(CA,IA,65000) + all-51 strict-mode sweep (43/43 refused, 8/8 passed); ruff on src/mcp_server/ (clean); business glossary lookup for 10 BT IDs (10/10 resolve)
- **Artifacts modified during review:**
  - `governance/dq-scorecards/mcp-bea-rpp-scorecard.md` — added remediation section and post-remediation summary
  - `governance/dq-results/mcp-bea-rpp-20260411T050916Z.json` — new file, 16/16 PASS post-remediation results
  - `governance/data-contracts/consumable-regional-price-parities.yaml` — Condition 7 carry-forward status flipped from FORWARD-ONLY OBLIGATION → DISCHARGED with back-reference to this post-review
- **Decision:** APPROVED for staff-engineer sign-off
- **Timestamp:** 2026-04-11
- **Reviewer:** @governance-reviewer
