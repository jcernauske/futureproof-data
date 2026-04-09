# Audit Trail: Logical Model - gold-onet-profiles

**Agent:** @semantic-modeler
**Spec:** gold-onet-profiles
**Stage:** Logical Model (Stage 2 of 3, Greenfield)
**Timestamp:** 2026-04-08
**Status:** PROPOSED -- awaiting human approval

## Inputs Read

1. **Approved conceptual model:** governance/models/gold-onet-profiles-conceptual.md (PROPOSED status, 7 entities, 7 relationships)
2. **Spec:** docs/specs/gold-onet-profiles.md (DRAFT, detailed schema tables for both Gold tables)
3. **Business glossary:** governance/business-glossary.json (76 terms, BT-055 through BT-072 are O*NET/Gold-specific)
4. **Pattern reference:** governance/models/gold-occupation-profiles-bls-ooh-logical.md (APPROVED, used as structural template)
5. **Config:** REQUIRE_HUMAN_APPROVAL = true (per CLAUDE.md)

## Artifact Produced

- **File:** governance/models/gold-onet-profiles-logical.md
- **Status:** PROPOSED

## Key Modeling Decisions

### 1. Two tables, single logical model document
Both consumable.onet_work_profiles (798 rows, bls_soc_code grain) and consumable.career_transitions (15,944 rows, bls_soc_code x related_bls_soc_code grain) are documented in one logical model because they are part of one spec and have a cross-table dependency (Table 2 checks Table 1 for work profile availability flags).

### 2. Attribute grouping follows conceptual entities
The 26 Work Profile attributes are organized into 8 logical groups matching conceptual entities: Occupation Identity, Human Edge Assessment, Burnout Assessment, Activity Profile Summary, Context Profile Summary, Data Quality Context, FutureProof Stat Mapping, Pipeline Metadata. This preserves semantic clarity while acknowledging physical denormalization.

### 3. CDE tagging conservative
Only 4 CDEs on Table 1 (bls_soc_code, hmn_score, burnout_score, burnout_drivers) and 2 on Table 2 (bls_soc_code, related_bls_soc_code). These are the attributes that directly back FutureProof stats/bosses or serve as the primary join keys. Rounded scores, availability flags, and suppression percentages are not CDEs.

### 4. Full derivation rules documented
HMN score (4-step ratio derivation), Burnout score (3-step normalize-and-average), Confidence tier (3-level classification), and all JSON array derivations are fully specified with formulas, null conditions, and scale interpretations. This enables implementation without ambiguity.

### 5. Null semantics are uniform
All 13 nullable fields on Table 1 are null for the same 24 partial-data occupations. There is no mixed nullability. Table 2 has zero nullable fields. This simplifies downstream consumer logic.

### 6. Open Decisions documented but not resolved
The three spec-level Open Decisions (human-intensive activity classification, burnout weighting, HMN formula approach) are documented with proposed approaches. The logical model uses the proposed approach; if human review changes a decision, only the derivation rules section needs updating -- the attribute definitions are stable.

## Alternatives Considered

| Decision Point | Alternative | Why Rejected |
|---------------|-------------|-------------- |
| Separate logical model per table | Two files: gold-onet-work-profiles-logical.md and gold-onet-career-transitions-logical.md | One spec = one model set. The cross-table dependency makes a single document clearer. Consistent with how the conceptual model handles it. |
| Include all 9 individual burnout elements as attributes | time_pressure through responsibility_health_safety (9 fields) | Spec only calls for 3 individual elements (time_pressure, work_hours, consequence_of_error). The remaining 6 are intermediate to burnout_score but not persisted. |
| Mark suppress_pct fields as CDE | They affect confidence_tier which affects data quality | They are quality metadata, not business-critical data elements. Confidence_tier itself is not a CDE either -- it is a quality classifier. |

## Stage Progression

| Stage | Status | Date | Notes |
|-------|--------|------|-------|
| Conceptual (Stage 1) | PROPOSED | 2026-04-08 | 7 entities, 7 relationships. Awaiting formal approval. |
| Logical (Stage 2) | PROPOSED | 2026-04-08 | This artifact. 26 + 14 attributes across 2 tables. |
| Physical (Stage 3) | NOT STARTED | -- | Blocked until logical model is approved. |
