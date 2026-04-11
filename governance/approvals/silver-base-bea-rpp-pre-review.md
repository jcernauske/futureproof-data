# Governance Review: silver-base-bea-rpp

**Review Type:** Pre-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-10
**Zone:** Silver
**Spec:** `docs/specs/silver-base-bea-rpp.md`
**Parent spec:** `docs/specs/raw-ingest-bea-rpp.md` (Bronze, APPROVED-WITH-CONDITIONS 2026-04-10)
**Verdict:** APPROVED (CHANGES APPLIED 2026-04-10)

---

## CHANGES APPLIED 2026-04-10

All three blocking issues from the initial review have been resolved in the spec. Re-verified by @governance-reviewer on 2026-04-10.

**Issue #1 — verification_status column.** RESOLVED.
- New column 11 `verification_status` added to `§Silver Schema` (string, required, enum `{bea_official, estimate}`).
- Derivation documented in `§Silver Transformations` step 8, referencing the 8-FIPS allow-list `{'06','15','11','34','05','28','19','40'}` and naming staff-review Ruling 2 / Condition 6 inline.
- P0 DQ rules added: (a) enum constraint on the value set, (b) `COUNT(*) WHERE verification_status='bea_official' = 8`, (c) every `bea_official` row's `state_fips` is in the 8-FIPS allow-list.
- Spot-checks table expanded to all 8 BEA-verified states, each asserting `verification_status = 'bea_official'` alongside the three derivations.

**Issue #2 — cite Bronze Ruling 2 in writing.** RESOLVED.
- `§Silver Transformations` step 8 cites `governance/approvals/raw-ingest-bea-rpp-staff-review.md` Ruling 2 / Condition 6 inline.
- New `§Bronze Staff Review Conditions` section added, naming Condition 6 as "implemented here" with schema and DQ pointers, and Condition 7 as forward-only (carry-forward to Gold and MCP specs).
- Governance artifacts list now includes BT-105 (Data Verification Status), closing the glossary-lineage loop from advisory #1.

**Issue #3 — data_year anchor rule.** RESOLVED.
- New P0 rule `data_year = 2024 (P0 — mirror of Bronze RAW-BEA-010)` added to `§DQ Rules`.
- Existing `COUNT(DISTINCT data_year) = 1` rule retained as the supersession invariant. The two rules now form the complete contract carry-forward pattern from Bronze.

**Bonus improvements beyond the required scope.**
- Spot-checks expanded from 4 states to all 8 BEA-verified states (CA, HI, DC, NJ, AR, MS, IA, OK), each carrying `state_abbr`, `census_region`, `purchasing_power_multiplier` (±0.001), and `verification_status`. This fully addresses advisory #4 at the Silver level — no further DQ expansion needed.
- Data dictionary target updated to 11 columns. Business glossary targets now include BT-103 (USPS State Abbreviation), BT-104 (Census Region), and BT-105 (Data Verification Status).

**Verdict flip:** CHANGES REQUESTED → APPROVED. Silver-base-bea-rpp may proceed to @data-steward.

---

## TL;DR

The spec is well-shaped, correctly scoped, and the Bronze foundation is clean enough to unblock Silver. The transformations (state_abbr, census_region, purchasing_power_multiplier) are structural and low-risk. The DQ rule set is strong and the schema is tight.

**But the spec directly contradicts the Bronze staff-engineer review on the single most important inherited constraint.** The Bronze staff review Ruling 2 explicitly assigns `verification_status` as a deferred item **for this Silver spec to implement**, with a named owner (@primary-agent on silver-base-bea-rpp) and a prescribed DQ rule. The Silver spec's "Inherited Constraints from Bronze" section reverses the ruling and says the column is "deferred" — with no further owner, no further target zone. There is nowhere left for this column to go. Either the Silver spec misread the ruling, or it is attempting to silently re-defer an obligation that the Bronze staff sign-off marked as a Silver-spec precondition.

This is blocking. It is the reason Silver was unblocked. The spec needs a one-section rewrite to honor Condition 6 of the Bronze staff review before @data-steward begins.

A second issue is the DQ spot-check coverage. The spec anchors CA, IA, AR, DC. Bronze's HIGH-4 finding called out that 6 of 8 spec-verified values were unanchored, and named HI/DC/NJ/MS/IA/OK as the missing six. Silver has the opportunity to close this gap at zero cost. The current spec picks up DC + IA but still leaves HI, NJ, MS, OK unanchored. Not a blocker — it is the Bronze refresh PR that is supposed to fix this at the Bronze DQ level — but an advisory for @dq-rule-writer.

The remaining items are small clarifications and housekeeping.

---

## Pre-Implementation Checklist

- [x] Spec has a clear problem statement and success criteria
- [x] Input data sources are identified with paths (`bronze.bea_rpp`, 51 rows, COMPLETE)
- [x] Output artifacts are defined with paths and formats (`base.bea_rpp`, grain `state_fips`)
- [x] Transformations are described (what changes, why) — five derivations plus two passthroughs
- [x] Zone assignment is correct (Silver)
- [x] Primary implementation agent is identified (@primary-agent)
- [x] DQ rule categories are specified (row count, uniqueness, range, referential, spot-check, invariant)
- [x] CDE mapping impact is assessed (state_abbr, census_region, purchasing_power_multiplier flagged as strong CDE candidates)
- [x] Lineage scope is defined (single `bronze.bea_rpp` → `base.bea_rpp` transformation)
- [x] Breaking changes flagged — none; this is greenfield Silver
- [x] Testing approach is defined (EDA, DQ rules, chaos pack, adversarial audit)

### Data Model Gate (Silver greenfield, Base zone)

The spec acknowledges `governance/models/silver-base-bea-rpp-{conceptual,logical,physical}.md` as deliverables for @semantic-modeler in workflow step 3. Models do not yet exist — they are scheduled to be produced before @primary-agent builds. This is the correct greenfield ordering. Gate is not yet due for enforcement (it will be at the pre-build governance step); flagged here so downstream agents know to produce all three before any code lands.

- [ ] Conceptual model — PENDING, scheduled
- [ ] Logical model — PENDING, scheduled
- [ ] Physical model — PENDING, scheduled

### Bronze-inherited open conditions from staff review

| Condition | Bronze ruling | Silver spec disposition | Status |
|---|---|---|---|
| Condition 4 (contract DRAFT→ACTIVE status field) | Must be fixed immediately, in-session | Not Silver's concern — Bronze contract artifact | N/A to Silver |
| Condition 6 (verification_status column) | Deferred TO Silver, owner @primary-agent, with prescribed P0 DQ rule | Silver spec says "No per-row verification_status column added (deferred per staff-engineer ruling)" — WRONG direction of deferral | **BLOCKING** |
| Condition 7 (MCP hallucination guard) | Deferred to MCP spec | N/A to Silver | N/A to Silver |
| HIGH-4 (6 missing per-state spot-checks) | Pre-refresh blocker, Bronze refresh PR | Silver picks up DC + IA, leaves HI/NJ/MS/OK unanchored at Silver | ADVISORY (below) |

---

## Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | CHANGES REQUESTED | Spec's "Inherited Constraints from Bronze" section contradicts Bronze staff review Ruling 2. Ruling 2 explicitly defers `verification_status` **to this Silver spec** as a required column with a named owner and a prescribed P0 DQ rule. The Silver spec attempts to re-defer the column with no onward owner. This is the reason the Bronze staff sign-off conditionally unblocked Silver — removing it breaks the condition chain. | Rewrite §Inherited Constraints to say: "Add `verification_status` column (enum: `bea_official` \| `estimate`) derived from a hard-coded allow-list of the 8 BEA-verified geo_fips codes (`06` CA, `15` HI, `11` DC, `34` NJ, `05` AR, `28` MS, `19` IA, `40` OK). Carry forward the Bronze row's value where the row is in the allow-list, else mark `estimate`." Add to §Silver Schema as an 11th column (required, string). Add to §DQ Rules: P0 rule asserting `count(verification_status='bea_official') == 8` while 43 estimates remain; the rule flips to `== 51` once the live BEA API refresh lands. Reference the rule in the column's data dictionary entry. Add to §Spot checks: assert each of the 8 allow-list state_fips has `verification_status='bea_official'` and each of the non-allow-list state_fips has `verification_status='estimate'`. |
| 2 | CHANGES REQUESTED | Silver spec does not reference the Bronze staff review Ruling 2 or Conditions 6/7 anywhere. A future reviewer has no link from this spec back to the reason the column exists. The audit trail loop from Bronze sign-off to Silver implementation must be closed in writing. | Add a "Bronze Staff Review Conditions" subsection under §Inherited Constraints that cites `governance/approvals/raw-ingest-bea-rpp-staff-review.md` Ruling 2 by name, quotes the prescribed rule text, and marks Condition 6 as "implemented in this spec" with the schema/DQ pointers from issue #1. Also note that Condition 7 (MCP hallucination guard) propagates forward to a future `mcp-bea-rpp` spec and Silver must preserve `verification_status` through to Gold so it is available at MCP time. |
| 3 | CHANGES REQUESTED | The spec's §DQ Rules has no rule closing the loop on the data_year replacement-supersession inheritance. The rule `COUNT(DISTINCT data_year) = 1` is listed (good), but without a concrete value assertion it does not catch a bad refresh that loads the wrong year. Bronze has RAW-BEA-010 asserting `data_year = 2024` — Silver needs the same assertion to carry the contract forward. | Strengthen `COUNT(DISTINCT data_year) = 1` to a two-part rule: (a) `COUNT(DISTINCT data_year) = 1` (supersession invariant), (b) `data_year = 2024` (vintage anchor — update the literal when refresh lands). This matches the existing Bronze rule pattern and keeps the contract chain tight across zones. |
| 4 | ADVISORY | Spot-check coverage. Spec anchors CA, IA, AR, DC. Bronze HIGH-4 called out HI, NJ, MS, OK as also lacking DQ anchors. Silver cannot fix the Bronze gap (that is a Bronze refresh PR deliverable) but it can add its own Silver-zone spot checks for all 8 verified states at effectively zero cost. The Silver spot-check is different in intent from the Bronze one — Silver verifies that the derivations (state_abbr, census_region, purchasing_power_multiplier) land correctly for every verified row, not just that rpp_all_items round-trips. Adding 4 more (HI `state_abbr='HI'`/`West`/≈0.9091, NJ `state_abbr='NJ'`/`Northeast`/≈0.9191, MS `state_abbr='MS'`/`South`/≈1.1494, OK `state_abbr='OK'`/`South`/≈1.1390) closes the transformation correctness audit for the full verified set and gives the Silver DQ suite 8/8 anchored state-level checks. Not blocking; strongly recommended. | Advisory for @dq-rule-writer: expand §Spot checks from 4 states to all 8 BEA-verified states (CA, HI, DC, NJ, AR, MS, IA, OK). Each spot check should assert the three derivations (`state_abbr`, `census_region`, `purchasing_power_multiplier` within ±0.001) plus a `verification_status='bea_official'` check for the row. These are the Silver-zone equivalents of Bronze's RAW-BEA-007/008 and the proposed RAW-BEA-020..025 that will land in the Bronze refresh PR. |
| 5 | ADVISORY | The state_abbr and census_region lookups are structural static data (51 rows each, fixed properties of US geography). The spec correctly notes this is "structural, not entity-specific data" and allows in-code constants. Recommend that @primary-agent place both lookups in a single module (e.g., `src/silver/_us_state_reference.py`) with a module-level docstring citing the FIPS → USPS mapping from the U.S. Postal Service and the Census region assignment from the U.S. Census Bureau, and that the module include a self-check (assert len == 51, assert all FIPS keys match `VALID_STATE_FIPS` from `src/raw/bea_rpp_ingestor.py`, assert exactly 4 distinct regions). This prevents silent drift between the Bronze allow-list and the Silver lookup. | Advisory for @primary-agent. Not blocking. |
| 6 | ADVISORY | DC census region quirk. The spec acknowledges DC sits in `South` per Census convention "despite its Northeast-like RPP; this is a documented quirk, not a bug." Good. Recommend this quirk be called out in the data dictionary entry for `census_region` and in BT-104 (Census Region) so a downstream consumer who sees DC's 109.9 RPP paired with `census_region='South'` has a one-click explanation. | Advisory for @doc-generator. Not blocking. |
| 7 | ADVISORY | The spec lists `source_load_date` as a passthrough from Bronze `load_date`. Bronze also has `ingested_at` (timestamp). The Silver spec's `ingested_at` is the Silver promotion timestamp, not the Bronze one. This is correct behavior but the column-name collision between Bronze.ingested_at and Silver.ingested_at could confuse a lineage reader. Recommend the data dictionary entry for Silver.ingested_at explicitly states "Silver promotion timestamp, distinct from Bronze.ingested_at". | Advisory for @doc-generator. Not blocking. |
| 8 | ADVISORY | Condition 7 forward-propagation. The MCP hallucination guard from Bronze HIGH-3 is deferred to the MCP spec, but it depends on `verification_status` reaching MCP intact. Silver is the first hop in that chain. Once issue #1 is resolved, Silver must preserve the column into Gold so it is available at MCP. This is a note for the Gold spec author, but mentioning it here closes the audit trail for the staff-engineer at post-review time. | Advisory: add a note in §Cross-Source Integration or a new §Forward Propagation Notes saying "`verification_status` must be carried forward to `consumable.regional_price_parities` so the MCP tool `get_regional_price_parity` can satisfy Bronze Condition 7." |

---

## Blocking gaps before @data-steward can run

1. **Issue #1 — verification_status column rewrite.** The Silver spec's §Inherited Constraints section must be corrected to implement Bronze Condition 6, not reverse it. This changes the schema (adds column 11), adds at least one P0 DQ rule, and amends spot-check assertions. @data-steward cannot confirm business terms for a schema that is missing one of its columns.
2. **Issue #2 — cite Bronze Ruling 2 in writing.** @data-steward's glossary confirmation should include a pointer to the Bronze ruling so the BT-098/099/100/101/102 lineage is preserved and so the future BT-103/104 entries don't get orphaned if the spec changes again.
3. **Issue #3 — data_year anchor rule.** Trivial, but should be in the spec before @dq-rule-writer starts so the rule set is complete on first draft.

Issues 4–8 are advisories and do not block @data-steward. They block @dq-rule-writer (issue 4), @primary-agent (issue 5), @doc-generator (issues 6, 7), and the Gold spec author (issue 8) respectively, and should be addressed at their respective workflow steps without further review cycles.

---

## Decision Rationale

The spec has genuine quality. The transformations are right, the DQ suite is strong, the grain and dedup are coherent, and the agent workflow mirrors the project's standard greenfield Silver pipeline. The temporal-strategy and entity-resolution skip recommendations are defensible (state FIPS is canonical, single-vintage reference table).

The reason for CHANGES REQUESTED is a single, discrete, 30-minute rewrite of one section. The verification_status obligation is not optional — it was the explicit condition under which Bronze unblocked Silver. Shipping this spec without that column would:

1. Break the Bronze contract chain (the staff sign-off would no longer be honored by its named successor).
2. Force Condition 7 at the MCP tier to fall back on either runtime hard-coding of the 8-state allow-list or a full re-derivation of provenance, neither of which is acceptable.
3. Silently deflate the governance audit trail: a reviewer reading the Silver staff review with no verification_status column would either have to discover the Bronze ruling independently or miss the obligation entirely.

The other blocking issue (#3, data_year anchor) is a small, obvious contract carry-forward from Bronze that the current spec simply missed. Five minutes to fix.

Everything else is advisory and can be addressed within the natural flow of the downstream agents. No REJECTED verdict because the spec is fundamentally sound; this is a targeted CHANGES REQUESTED with specific, actionable edits.

Silver-base-bea-rpp **may NOT proceed to @data-steward** until issues 1, 2, and 3 are resolved. Expected time to resolution: <1 hour of spec-author edits. No re-review required if the edits match the prescribed resolutions above — this pre-review can be updated in place with a "CHANGES APPLIED" note and the verdict flipped to APPROVED.

---

## Advisory notes for downstream agents (post-unblock)

These are for the workflow agents to internalize once issues 1–3 are fixed. They are NOT blocking @data-steward but should be picked up at the right workflow step:

- **@data-steward:** Confirm BT-103 (USPS State Abbreviation) and BT-104 (Census Region). Include BT-104's DC-in-South quirk in the definition text. Verify that BT-098..102 are still correctly scoped for the Silver transformation context (no term drift). If issue #1 lands a `verification_status` column, consider whether a BT-105 for "Data Verification Status" is warranted or whether it can be documented as a column-level enum without a glossary term.
- **@semantic-modeler:** Physical model must include `verification_status` if issue #1 lands. Conceptual model must reference BT-103 and BT-104 and (conditionally) BT-105. Mermaid `erDiagram` required for all three stages.
- **@data-analyst:** EDA should verify (a) all 51 state_abbr values are uppercase 2-char USPS codes, (b) all 4 census regions represented with expected state counts (Northeast: 9, Midwest: 12, South: 17, West: 13 — note DC counts in South, bringing South to 17 total), (c) purchasing_power_multiplier numerical range empirically matches `[0.7, 1.3]`, (d) the inverse invariant `multiplier × rpp_all_items ≈ 100.0` holds to tolerance 0.01 for all 51 rows, (e) the 8 verified-state derivations match the spot-check expected values to ±0.001.
- **@dq-rule-writer:** See advisory #4. Expand spot-checks to cover all 8 BEA-verified states. Make the `verification_status` allow-list rule P0. Match Bronze's RAW-BEA-010 `data_year = 2024` rule at Silver.
- **@primary-agent:** See advisory #5. Use a single static lookup module for both state_abbr and census_region. Include `verification_status` derivation from the 8-state allow-list. Use `compute_grain_id` with `prefix='rpp'` — do NOT change the prefix, the Gold spec joins on record_id assumptions.
- **@chaos-monkey:** Scenario pack should include `verification_status` mutations (flip a verified row to 'estimate' and vice versa) in addition to the standard Silver derivation mutations.
- **@adversarial-auditor:** The spec's inherited caveat (43/51 estimates) is pre-disclosed; Silver must not claim more verification than Bronze. Verify this honesty is preserved end-to-end — in the Silver data contract quality_tier, in the data dictionary, and in the CDE tagging rationale.
- **@doc-generator:** BT-103, BT-104 glossary entries. Data dictionary must include the DC census region quirk callout (advisory #6) and the Silver.ingested_at vs Bronze.ingested_at disambiguation (advisory #7). Column count for `base.bea_rpp` is 10 in the current spec; after issue #1 lands, it will be 11.

---

## Artifacts referenced

| Path | Role |
|---|---|
| `/Users/jcernauske/code/bright/futureproof-data/docs/specs/silver-base-bea-rpp.md` | Spec under review |
| `/Users/jcernauske/code/bright/futureproof-data/docs/specs/raw-ingest-bea-rpp.md` | Parent spec (Bronze, COMPLETE) |
| `/Users/jcernauske/code/bright/futureproof-data/governance/approvals/raw-ingest-bea-rpp-staff-review.md` | Source of Conditions 6 and 7 (Rulings 2 and 3) — basis for blocking issues #1 and #2 |
| `/Users/jcernauske/code/bright/futureproof-data/governance/adversarial-audits/raw-ingest-bea-rpp.md` | Source of HIGH-3 and HIGH-4 findings — basis for advisories #4 and #8 |
| `/Users/jcernauske/code/bright/futureproof-data/governance/temporal/raw-ingest-bea-rpp.md` | Temporal strategy (replacement-supersession, single-vintage) — Silver inherits |
| `/Users/jcernauske/code/bright/futureproof-data/governance/business-glossary.json` | Confirms BT-098..102 exist; BT-103, BT-104 to be added this spec |
| `/Users/jcernauske/code/bright/futureproof-data/governance/dq-rules/raw-ingest-bea-rpp.json` | Bronze DQ rule set — the `data_year = 2024` rule pattern to mirror at Silver (issue #3) |

---

*— End of Pre-Implementation Review —*
