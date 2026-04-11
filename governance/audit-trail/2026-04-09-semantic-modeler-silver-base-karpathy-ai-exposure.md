# Audit Trail: Semantic Modeler -- silver-base-karpathy-ai-exposure

**Agent:** @semantic-modeler
**Spec:** docs/specs/raw-ingest-karpathy-ai-exposure.md (Zone 2: Silver)
**Date:** 2026-04-09
**Mode:** Greenfield (new Silver table, no existing code)
**Config:** REQUIRE_HUMAN_APPROVAL = true (per CLAUDE.md)

---

## Stage Progression

| Stage | Artifact | Status | Timestamp |
|-------|----------|--------|-----------|
| 1. Conceptual | governance/models/silver-base-karpathy-ai-exposure-conceptual.md | PROPOSED | 2026-04-09 |
| 2. Logical | governance/models/silver-base-karpathy-ai-exposure-logical.md | PROPOSED | 2026-04-09 |
| 3. Physical | governance/models/silver-base-karpathy-ai-exposure-physical.md | PROPOSED | 2026-04-09 |

All three stages produced. All PROPOSED pending human review per REQUIRE_HUMAN_APPROVAL = true.

---

## Inputs Consumed

| Input | Purpose |
|-------|---------|
| docs/specs/raw-ingest-karpathy-ai-exposure.md | Silver schema, transformations, DQ rules |
| governance/eda/raw-karpathy-ai-exposure-eda.md | Data profiling: SOC coverage (84.8%), score distribution, broad code analysis |
| governance/business-glossary.json (BT-094 through BT-097) | Business term cross-references |
| governance/models/silver-base-bls-ooh-*.md | Existing model patterns for Silver Base zone |
| governance/domain-context.md | Domain vocabulary and Karpathy methodology context |

---

## Key Modeling Decisions

### 1. Grain change from slug to soc_code

**Decision:** Silver grain is soc_code (not slug as in Bronze).
**Rationale:** The downstream pipeline joins exclusively on SOC code. Slug is a source-specific identifier with no meaning outside the Karpathy dataset. Changing the grain to soc_code aligns this table with base.bls_ooh and all consumable tables.
**Trade-off:** soc_code is nullable (~5% of rows), which weakens the grain constraint. Uniqueness is enforced only on non-null values.

### 2. Nullable natural key (soc_code)

**Decision:** Allow null soc_code for unresolved occupations.
**Rationale:** Spec explicitly requires preserving unresolved rows for completeness. Dropping them would lose Karpathy assessment data. The null rows do not participate in downstream joins but are available for manual resolution or future matching.
**Alternative considered:** Dropping unresolved rows entirely. Rejected because the spec requires preservation and the data may be resolvable in future iterations.

### 3. Broad SOC code expansion as a row-multiplying transformation

**Decision:** Expand broad codes (XX-XXX0) to constituent detailed codes, propagating exposure score and rationale identically.
**Rationale:** Spec step 4 requires this. The alternative (keeping broad codes and matching by prefix downstream) would push complexity into every downstream consumer. Expanding at Silver is the correct normalization point.
**Impact:** Row count increases from 342 to ~500+. Post-expansion deduplication is needed.

### 4. record_id fallback for null soc_code

**Decision:** Use slug as the hash input when soc_code is null.
**Rationale:** compute_grain_id requires a non-null input. Slug is the Bronze grain key and is guaranteed non-null and unique. This produces a stable, deterministic record_id for every row.
**Alternative considered:** Using a composite of slug + category. Rejected as unnecessarily complex; slug alone is unique.

### 5. Single denormalized table (matching existing Silver pattern)

**Decision:** Flatten all conceptual entities into one table.
**Rationale:** All relationships are 1:1 or 1:0..1. Matches base.bls_ooh and base.college_scorecard patterns. 11 columns is a lean table with no normalization benefit from splitting.

### 6. No cross-validation fields carried to Silver

**Decision:** Drop median_pay_annual, num_jobs_2024, entry_education from Bronze.
**Rationale:** Cross-validation was completed at Bronze (EDA confirms perfect wage alignment). These fields duplicate base.bls_ooh data. Carrying them would create redundancy.
**Alternative considered:** Keeping num_jobs_2024 for deduplication tiebreaking. The deduplication logic can reference the Bronze table directly during transformation; it does not need to persist in Silver.

### 7. exposure_score as INTEGER (not DOUBLE or VARCHAR)

**Decision:** INTEGER type with CHECK 0-10.
**Rationale:** Score is used in arithmetic derivations at Gold (MIN(11 - score, 10) and MAX(score, 1)). Integer typing avoids unnecessary casting. The score is discrete with 11 possible values.

---

## Business Glossary Cross-References

| Model Level | Terms Referenced |
|-------------|-----------------|
| Conceptual | BT-027 (SOC Code), BT-094 (AI Exposure Score), BT-095 (AI Exposure Rationale), BT-096 (SOC Resolution Method), BT-097 (BLS Match Flag) |
| Logical | BT-015 (Record ID), BT-016 (Source Load Date), BT-017 (Ingested At), BT-027, BT-028 (Occupation Title), BT-094, BT-095, BT-096, BT-097 |
| Physical | Same as Logical (1:1 logical-to-physical mapping for all columns) |

All referenced terms exist in governance/business-glossary.json. BT-094 through BT-097 were proposed by @data-steward for this spec. BT-015 through BT-017 are shared pipeline infrastructure terms. BT-027 and BT-028 are shared SOC-domain terms from base.bls_ooh.

---

## Open Issues

| # | Issue | Blocking | Owner |
|---|-------|----------|-------|
| 1 | slug and category have no business glossary terms | No | @data-steward |
| 2 | Exact row count unknown until implementation (~500+ estimated) | No | @primary-agent |
| 3 | BT-094 through BT-097 are "proposed" not "approved" in glossary | No (non-blocking for modeling, but must be approved before Gold) | @data-steward / human |
