# Audit Trail: @doc-generator — silver-base-college-scorecard

**Date:** 2026-04-06
**Agent:** @doc-generator
**Spec:** docs/specs/silver-base-college-scorecard.md

---

## Actions Taken

### 1. Data Dictionary Updated (`governance/data-dictionary.json`)

**Added:** `base.college_scorecard` table entry with 18 column definitions.

All 18 columns documented with:
- Plain-English definitions suitable for business users
- CDE flags carried from physical model (4 CDE columns: unitid, earnings_1yr_median, earnings_2yr_median, debt_median)
- PII flags (0 PII columns)
- Business term cross-references (BT-001 through BT-017, plus pending BT-018 for institution_control)
- DQ rule cross-references (35 rules from SLV-CS-001 through SLV-CS-035)
- Source column lineage (raw field name and transformation applied)
- Nullability semantics documented for all 5 nullable fields

**Also added:** `control` column to `raw.college_scorecard` entry to reflect the raw schema update required for the Silver `institution_control` field.

**Existing Bronze entries preserved:** All `raw.college_scorecard` column definitions retained unchanged.

### 2. Data Contract Created (`governance/data-contracts/base-college-scorecard.yaml`)

**New file.** Silver base table data contract with:
- Full 18-column schema with types, nullability, CDE/PII flags, business terms, and descriptions
- Domain constraints (CHECK constraints) for cipcode format, cip_family format, credential_level range, earnings ranges, debt range, institution_control allowed values, and completions non-negativity
- Quality thresholds derived from EDA findings and DQ rules:
  - Null rate ceilings for nullable fields (70%, 65%, 68%, 12%, 12%)
  - Row count range (60,000-80,000)
  - Institutional coverage (2,200-3,000 distinct)
  - CIP code/family coverage ranges
- Semantic versioning breaking change policy
- Lineage reference to `governance/lineage/silver-base-college-scorecard-20260406T200000Z.json`
- Status: `draft` (requires @staff-engineer approval to become `active`)

### 3. README Updated (`README.md`)

**Added sections:**
- **Data Models** — Mermaid diagrams for all three modeling levels (conceptual, logical, physical)
- **Tables** — Summary table of Bronze and Silver tables with zone, row counts, grain, and descriptions
- **Business Glossary** — All 17 terms (BT-001 through BT-017) with human-readable names, categories, and definitions. Business term IDs dereferenced into readable names.
- **Governance** — Directory listing of all governance artifacts
- **Key Design Decisions** — 5 major design decisions documented for project onboarding

---

## Interpretation Decisions

1. **institution_control business term:** Noted as "pending BT-018" per the physical model's open issue. No business term exists yet in the glossary for this field. Used the physical model's description as the dictionary definition.

2. **DQ rule cross-references:** Mapped each Silver column to its relevant DQ rules from the 35-rule set in `governance/dq-rules/silver-base-college-scorecard.json`. Some columns participate in multiple rules (e.g., unitid appears in grain uniqueness, completeness, coverage, and range rules).

3. **raw.college_scorecard control column:** Added a `control` entry to the Bronze dictionary to reflect the raw schema update noted in the spec (option a: update raw ingestor to include CONTROL field). This column was not in the original Bronze dictionary because the raw ingestor was updated after the initial Bronze documentation.

4. **Quality thresholds in contract:** Derived from EDA evidence cited in DQ rules. Used the DQ rule thresholds (which include headroom above observed values) rather than the raw observed rates.

5. **README business glossary:** Dereferenced all BT-XXX IDs into human-readable names and condensed definitions to fit a table format while preserving the key information a business user needs.
