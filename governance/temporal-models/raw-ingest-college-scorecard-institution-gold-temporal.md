## Temporal Design: raw-ingest-college-scorecard-institution — Gold Enrichment

**Date:** 2026-04-16
**Agent:** @temporal-modeler
**Domain:** Higher Education Outcomes — Institution-Level Cost Enrichment at Gold
**Upstream Spec:** docs/specs/raw-ingest-college-scorecard-institution.md (§Zone 3)
**Bronze Temporal Assessment:** governance/temporal-models/raw-ingest-college-scorecard-institution-temporal.md
**Silver Temporal Assessment:** governance/temporal-models/silver-base-college-scorecard-institution-temporal.md
**Bitemporal Required:** NO
**Verdict:** APPROVED — no temporal modeling required beyond existing

---

### Summary (≤70 words)

Gold enrichment adds 7 institution-level cost columns to `consumable.career_outcomes` via LEFT JOIN on `unitid`. No new temporal dimension is introduced. Both source tables share the same "most-recent-cohort" vintage (2023 data published 2024/2025), so there is no mixed-vintage risk. The `promoted_at` refresh is a correct idempotent-promote marker, not data drift. No bitemporal schema is warranted. **Verdict: APPROVED.**

---

### 1. Vintage Inheritance — No Mixed-Vintage Risk

The LEFT JOIN combines two Silver inputs that share vintage by construction:

| Input | Vintage | Grain | Source |
|-------|---------|-------|--------|
| `base.college_scorecard` (program-level) | Most-Recent-Cohort (2023 cohort, published 2024/2025) | cipcode × credlev × unitid | College Scorecard Field-of-Study |
| `base.college_scorecard_institution` (institution-level) | Most-Recent-Cohort (2023 cohort, published 2024/2025) | unitid | College Scorecard Institution-Level |

Both tables are derived from the same College Scorecard annual release. The Silver temporal assessment established the vintage as "most recent cohort" and inherits that classification from Bronze. The Gold enrichment is therefore a **same-vintage, same-snapshot** join — no temporal alignment logic is needed, and no record will describe program-year 2023 with institution-year 2019 (or any other temporally inconsistent pairing).

If a future annual-refresh spec is introduced, the two Silver tables must refresh in lockstep (documented reassessment trigger in both Bronze and Silver temporal docs). Until that spec exists, vintage alignment is a ground truth of the join, not a gap.

---

### 2. `promoted_at` Refresh Semantics

The enrichment runs as a **full idempotent re-promote** (§Enrichment Mode, notes 4 and 6 of the spec), not an `ALTER TABLE ... UPDATE`. Consequence for transaction time:

- Every row of `consumable.career_outcomes` will have its `promoted_at` timestamp advance to the new promote time.
- This is **semantically correct**, not data drift. `promoted_at` is defined as "when this row was written in this snapshot," and every row is rewritten by design.
- Transaction-time provenance for the prior state remains fully recoverable via Iceberg snapshot history (time travel on the `consumable.career_outcomes` table).
- Consumers who treat `promoted_at` as "last modified" will see it advance — this matches the actual semantics of a full re-promote and is consistent with the behavior of every other Gold re-promote in this project.

No action required. `promoted_at` continues to do exactly what it was designed to do.

---

### 3. Bitemporal Schema — Not Warranted

Strong default: bitemporal modeling is not warranted for a hackathon-scope display enrichment.

| Question | Answer |
|----------|--------|
| Does enrichment introduce a valid-time period? | No — 7 cost fields, all point-in-time sticker/net/tuition values. |
| Does any downstream consumer need "cost as of date X"? | No — MCP `get_school_programs` and `get_career_paths` read current cost only. |
| Does enrichment introduce amendment / correction semantics? | No — corrections are handled by upstream re-ingest + full re-promote; Iceberg snapshot history is sufficient. |
| Would SCD Type 2 change any pipeline behavior today? | No — would add `valid_from` / `valid_to` columns that are always trivially `load_date` / `NULL`, creating maintenance burden without solving a query need. |
| Is there a reassessment trigger? | Yes — if an annual-refresh pipeline is introduced, or any spec asks for "cost at time of matriculation" or year-over-year cost trends, revisit at all three zones. |

Gold inherits the Silver/Bronze decision cleanly. YAGNI applies.

---

### 4. Schema Changes

**None required beyond what §Zone 3 of the spec already defines.** The 7 new columns (`net_price_annual`, `cost_of_attendance_annual`, `net_price_4yr`, `institution_control`, `tuition_in_state`, `tuition_out_of_state`, `room_board_on_campus`) are all point-in-time cost fields with no temporal suffixes, no `valid_from` / `valid_to` partners, and no supersession metadata. `promoted_at` already exists on the table.

---

### 5. Point-in-Time Query Support

**Not required.** If a future consumer asks "what did we know about institution X's net price on date Y?" — native Iceberg time travel against `consumable.career_outcomes` snapshot history is available without any schema change.

---

### 6. Trade-offs Considered

| Trade-off | Resolution |
|-----------|------------|
| Add `valid_from` / `valid_to` on the 7 new cost columns for forward compatibility? | Rejected. Silver has no valid-time columns; Gold cannot fabricate them. |
| Treat `promoted_at` refresh as drift and pin rows to original promote time? | Rejected. Idempotent re-promote is the established pattern; `promoted_at` semantically IS the re-promote marker. |
| Add a dedicated `institution_vintage_year` column? | Rejected for this spec. Can be added with minimal cost if an annual-refresh spec is authored. Not needed today. |
| Skip this Gold temporal review because Silver already approved? | Rejected. Explicit inheritance record completes the per-zone governance trail. |

---

### 7. Reassessment Trigger

Revisit if **any** of the following ship:

- An annual-refresh spec that loads multiple vintages of College Scorecard institution data into the same Silver table (would require SCD Type 2 at Silver, propagating to Gold).
- A feature spec requesting "cost of attendance at time of matriculation" or year-over-year cost trend display.
- A spec that decouples the two Silver inputs' refresh cadences (would reintroduce mixed-vintage risk at the Gold LEFT JOIN).

Until one of those ships, the current design is correct.

---

### 8. Audit Trail

- Bronze assessment referenced: `governance/temporal-models/raw-ingest-college-scorecard-institution-temporal.md`
- Silver assessment referenced: `governance/temporal-models/silver-base-college-scorecard-institution-temporal.md`
- Gold spec §Zone 3 referenced: `docs/specs/raw-ingest-college-scorecard-institution.md` lines 233–323
- Decision: NO bitemporal schema at Gold. Inherit from Silver. Vintage alignment is ground truth of the same-snapshot join.
- Reassessment trigger: annual-refresh pipeline, time-of-matriculation semantics, or decoupled refresh cadences.
- Verdict: **APPROVED — no temporal modeling required beyond existing.**

---

*— End of Gold Temporal Assessment —*
