# Audit Trail: Business Glossary — silver-base-college-scorecard

**Date:** 2026-04-06
**Agent:** @data-steward
**Mode:** Greenfield
**Domain:** Higher Education Outcomes
**Spec:** docs/specs/silver-base-college-scorecard.md

---

## Business Term Proposals: silver-base-college-scorecard

### New Terms Proposed

| Term ID | Term | Source | Category | Status |
|---------|------|--------|----------|--------|
| BT-001 | UNITID | external-standard | entity | AUTO-APPROVED |
| BT-002 | Institution Name | external-standard | entity | AUTO-APPROVED |
| BT-003 | CIP Code | external-standard | classification | AUTO-APPROVED |
| BT-004 | Program Name | external-standard | entity | AUTO-APPROVED |
| BT-005 | CIP Family | domain-standard | classification | AUTO-APPROVED |
| BT-006 | CIP Family Name | domain-standard | classification | AUTO-APPROVED |
| BT-007 | Credential Level | external-standard | classification | AUTO-APPROVED |
| BT-008 | Credential Description | external-standard | classification | AUTO-APPROVED |
| BT-009 | Median Earnings 1-Year Post-Completion | external-standard | measurement | AUTO-APPROVED |
| BT-010 | Median Earnings 2-Year Post-Completion | external-standard | measurement | AUTO-APPROVED |
| BT-011 | Median Debt at Completion | external-standard | measurement | AUTO-APPROVED |
| BT-012 | IPEDS Completions Count | external-standard | measurement | AUTO-APPROVED |
| BT-013 | Privacy Suppression | project-specific | regulatory | PROPOSED |
| BT-014 | Low Confidence Outcomes | project-specific | derived | PROPOSED |
| BT-015 | Record ID | project-specific | derived | PROPOSED |
| BT-016 | Source Load Date | project-specific | temporal | PROPOSED |
| BT-017 | Ingestion Timestamp | project-specific | temporal | PROPOSED |

### Existing Terms Referenced

None — this is the first glossary population for this project.

### Ambiguities Found

None. All terms have clear, unambiguous definitions sourced from either the NCES/IPEDS external standards, the College Scorecard data dictionary, or project-specific derivations documented in the spec.

---

## Source Attribution

| Term ID | Source Authority | Rationale |
|---------|----------------|-----------|
| BT-001 | NCES/IPEDS | UNITID is the authoritative federal identifier for postsecondary institutions. |
| BT-002 | NCES/IPEDS | INSTNM is the official institution name reported to IPEDS. |
| BT-003 | NCES CIP 2020 Taxonomy | CIP is the national standard for classifying instructional programs. |
| BT-004 | NCES CIP 2020 Taxonomy | Program descriptions are defined 1:1 with CIP codes in the taxonomy. |
| BT-005 | NCES CIP 2020 Taxonomy (2-digit series) | CIP families are the top level of the CIP hierarchy, a recognized grouping. |
| BT-006 | NCES CIP 2020 Taxonomy (2-digit series) | Labels for the 2-digit CIP family codes come from the taxonomy. |
| BT-007 | College Scorecard Data Dictionary | CREDLEV is defined by the Department of Education's Scorecard methodology. |
| BT-008 | College Scorecard Data Dictionary | CREDDESC labels are defined alongside CREDLEV in the data dictionary. |
| BT-009 | College Scorecard Methodology | EARN_MDN_HI_1YR is a College Scorecard-defined metric with specific cohort methodology. |
| BT-010 | College Scorecard Methodology | EARN_MDN_HI_2YR uses the same methodology as 1-year but different cohort window. |
| BT-011 | College Scorecard Methodology | DEBT_ALL_STGP_EVAL_MDN is a College Scorecard-defined debt metric. |
| BT-012 | NCES/IPEDS Completions Component | IPEDSCOUNT1/2 are reported through the IPEDS Completions survey. |
| BT-013 | Domain context + data observation | The concept is FERPA-driven but the threshold details (30 completers) are data-observed. Classified as project-specific. |
| BT-014 | Project derivation | Boolean flag invented by this project to mark small cohorts. No external standard. |
| BT-015 | Project derivation | Surrogate key computed by Brightsmith infrastructure. No external standard. |
| BT-016 | Project derivation | Pipeline metadata field tracking when data was loaded. |
| BT-017 | Project derivation | Pipeline metadata field tracking Silver zone write time. |

## Approval Decisions

- **Auto-approved (12 terms):** BT-001 through BT-012. These terms are defined by recognized external standards (NCES/IPEDS, College Scorecard data dictionary, CIP 2020 taxonomy). External standard definitions are authoritative and do not require human review per Brightsmith governance rules.
- **Proposed / Requires Human Approval (5 terms):** BT-013 through BT-017. These are project-specific terms (pipeline-derived concepts, project-invented flags, metadata fields). Per Brightsmith rules, project-specific terms always require human review regardless of the REQUIRE_HUMAN_APPROVAL toggle.

## Key Design Decisions

1. **Privacy Suppression (BT-013) classified as project-specific:** While the concept originates from FERPA/Department of Education rules, the specific threshold (30 completers) and the way we handle suppressed values (preserve as null) are data-observed and pipeline-specific. The domain context document recommended this classification.

2. **CIP Family (BT-005) classified as domain-standard:** The 2-digit CIP family grouping is a recognized level of the CIP taxonomy hierarchy, not a project invention. However, the extraction of the first 2 characters from the normalized code is a pipeline derivation. We classified the term itself as domain-standard because the concept exists in the taxonomy.

3. **Earnings terms include cohort methodology warning:** Both BT-009 and BT-010 definitions explicitly note that 1-year and 2-year figures are from different cohort windows, not longitudinal tracking. This is critical to prevent downstream misinterpretation (44.2% of rows show 2yr < 1yr earnings).

4. **CDE and PII flags excluded from glossary:** Per Brightsmith framework rules, CDE and PII designations live on physical data elements in data contracts, not on business terms. The same term can be a CDE in one context and not in another.
