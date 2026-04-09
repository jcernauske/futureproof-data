## PII Scan Audit Trail: gold-onet-profiles
**Date:** 2026-04-08
**Agent:** @pii-scanner
**Spec:** docs/specs/gold-onet-profiles.md
**Decision:** SKIP CONFIRMED

### Skip Justification

The spec recommends skipping @pii-scanner with justification: "Aggregated occupation-level data. No personal identifiers present." After independent assessment, this recommendation is **confirmed correct** for the following reasons:

### Assessment

**1. Data content analysis:**
Both Gold tables produced by this spec contain exclusively occupation-level aggregate data:

| Gold Table | Rows | Grain | Content |
|-----------|------|-------|---------|
| consumable.onet_work_profiles | 798 | bls_soc_code (one per occupation) | HMN score, Burnout score, activity summaries, confidence tiers, JSON aggregates |
| consumable.career_transitions | 15,944 | bls_soc_code x related_bls_soc_code | Occupation-to-occupation similarity pairs with titles and flags |

No field in either table contains, implies, or could be used to derive individual-level personal information. All fields are: SOC codes, occupation titles, derived numeric scores, JSON summaries of work activities/contexts, boolean flags, and metadata timestamps.

**2. Source data lineage:**
All source data flows from O*NET Silver tables (base.onet_occupations, base.onet_activity_profiles, base.onet_context_profiles, base.onet_career_transitions), which were already scanned at the raw ingest level (governance/audit-trail/pii-scan-raw-ingest-onet-2026-04-07.md) with **0 PII findings**. The Gold transformations only aggregate, pivot, and derive scores from these already-cleared sources. No new external data is introduced.

**3. Domain context corroboration:**
governance/domain-context.md O*NET PII Expectations section (line 894) confirms: "This dataset contains NO PII. All values are occupation-level aggregates derived from anonymized surveys conducted by the U.S. Department of Labor. Survey respondent identities are never included in the published database."

**4. Transformation analysis:**
The Gold transformations introduce no PII risk:
- HMN score: mathematical ratio of importance values across activity categories
- Burnout score: weighted average of normalized context values
- JSON arrays: top-N lists of activity/context element names and numeric values
- Career transitions: join of SOC codes with occupation titles and boolean flags
- All new fields are derived computations or static labels ("HMN", "Stage3Branching")

### Regulatory Implications
None. O*NET is a public federal dataset published under CC BY 4.0 by the U.S. Department of Labor. No GDPR, HIPAA, CCPA, or other privacy regulation applies to occupation-level aggregate data with no individual identifiers.

### Outcome
**SKIP CONFIRMED.** No PII scan execution required. No remediation, masking, or access restriction needed for PII reasons. @policy-engineer requires no PII-based policies for these tables.
