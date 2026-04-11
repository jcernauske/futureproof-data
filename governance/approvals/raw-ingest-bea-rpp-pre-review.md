# Governance Review: raw-ingest-bea-rpp (Pre-Implementation, Bronze Zone Only)

**Review Type:** Pre-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-10
**Scope of Review:** Bronze zone only (`raw.bea_rpp` table + BeaRppIngestor). Silver, Gold, and MCP phases are out of scope for this review and will be reviewed in separate spec runs.
**Verdict:** APPROVED (with ADVISORY notes)

---

## Pre-Implementation Checklist (Bronze Scope)

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Clear problem statement and success criteria | PASS | Problem is precisely framed: national salary figures are misleading without local cost-of-living adjustment. The example ($50K × 100/87.8 in Iowa vs. 100/110.7 in California) immediately demonstrates the gap. Bronze success criterion "Raw data lands in Iceberg table `raw.bea_rpp`" and "All 51 geographic entities ingested" are unambiguous. |
| 2 | Input data sources identified with paths | PASS | Primary: BEA API endpoint fully specified including TableName=SARPP, LineCode=1, Year=2024, GeoFips=STATE. Fallback: manual CSV at `data/raw/bea_cache/bea_rpp_2024.csv`. API key registration URL, env var name (`BEA_API_KEY`), dataset authority (BEA Regional Economic Accounts), license (U.S. Government Work / public domain), and update cadence (annual, February) are all documented. |
| 3 | Output artifacts defined with paths and formats | PASS | Iceberg table named (`raw.bea_rpp`), 8 raw schema fields specified with types and required flags, expected row count (51) given, grain and dedup grain declared, governance artifact paths listed in section "Governance Artifacts". |
| 4 | Transformations described (what changes, why) | PASS (Bronze-specific) | Bronze ingestor logic is clearly specified: (a) attempt BEA API first, (b) fall back to CSV cache on failure, (c) filter to LineCode=1 (exclude sub-components Goods/Services/Rents), (d) filter to state-level GeoFips (01-56 + 11 for DC, exclude metros), (e) parse `DataValue` string to float, (f) set User-Agent header. Each transformation has an explicit rationale. |
| 5 | Zone assignment correct | PASS | `raw.bea_rpp` correctly assigned to Bronze zone — raw, minimally transformed, source-of-record preservation. No business logic, no normalization of state codes (that's Silver). Correct per Brightsmith zone architecture. |
| 6 | Primary implementation agent identified | PASS | `@primary-agent` listed. Full 14-step agent workflow defined in spec — all Bronze-phase mandatory agents present (@data-analyst, @domain-context, @dq-rule-writer, @dq-engineer, @lineage-tracker, @cde-tagger, @doc-generator, @governance-reviewer post, @staff-engineer). |
| 7 | DQ rule categories specified | PASS | 9 Bronze DQ rules specified with P0/P1 severity: row count = 51 (P0), RPP range 80-130 (P0), RPP non-null (P0), geo_fips uniqueness (P0), geo_name non-null (P0), California spot check 108-115 (P0), Arkansas spot check 84-90 (P0), data_year = 2024 (P0), geo_fips format 2-digit numeric (P1). Spot checks against known 2024 values are exceptionally strong — they guard against stale data, wrong year fetched, or API schema drift. |
| 8 | CDE mapping impact assessed | PASS (implicit) | No PII expected (public U.S. Government data, state-level aggregates with no individuals). `geo_fips` and `state_abbr` (Silver) are likely CDEs as cross-source join keys. @cde-tagger is step 11 in the workflow. @pii-scanner is also scheduled to confirm absence of PII. |
| 9 | Lineage scope defined | PASS | Lineage artifact path defined: `governance/lineage/raw-ingest-bea-rpp-{timestamp}.json`. For Bronze, the lineage chain is short: BEA API (or CSV cache) → `raw.bea_rpp`. @lineage-tracker is step 10 in workflow. |
| 10 | Breaking changes to existing schemas flagged | PASS | No breaking changes. `raw.bea_rpp` is a new table. No existing table is modified by the Bronze phase. No joins to other pipeline tables at Bronze level (cross-source integration is a Gold-phase concern explicitly deferred in the spec). |
| 11 | Testing approach defined | PASS (implicit) | Not a standalone section (consistent with project convention). Success criteria, DQ rules, and known 2024 values define the testing surface. Staff engineer minimum of 10 tests for Raw zone applies. Spot-check values (CA, AR, HI, NJ, IA, MS, OK, DC) provide ready-made fixture data for unit tests. |

### Data Model Gate (Bronze Zone)

**Status:** SKIPPED — Bronze specs use physical-only models per framework. The raw schema table in section "Raw Schema" serves as the Bronze physical model. No conceptual/logical/physical three-stage progression is required for Bronze raw tables. Correct per Brightsmith zone architecture (only Silver/base and Gold/consumable zones require the 3-stage model gate). The spec correctly reserves the conceptual/logical/physical artifacts for Silver (`silver-base-bea-rpp-*`) and Gold (`gold-regional-price-parities-*`), which will be reviewed when those phases run.

---

## Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | ADVISORY | **Namespace convention drift.** Spec uses `raw.bea_rpp` as the Iceberg table FQN, but all existing source YAMLs in this project use `namespace: bronze` (see `domain/sources/onet.yaml`, `college_scorecard.yaml`, `bls_ooh.yaml`, `karpathy_ai_exposure.yaml`). Only `cip_soc_crosswalk.yaml` uses `namespace: raw`. The prior completed Bronze specs land tables in `bronze.<table>`, not `raw.<table>`. This is an inconsistency between the spec's prose and the actual project convention. | @primary-agent should clarify during implementation: either (a) create `domain/sources/bea_rpp.yaml` with `namespace: bronze` and land the table at `bronze.bea_rpp` (matches majority convention) or (b) explicitly reopen the naming decision. Not blocking — Brightsmith supports both. Recommend option (a) for consistency with the existing project tables. |
| 2 | ADVISORY | **Missing domain source YAML.** No `domain/sources/bea_rpp.yaml` exists. Every other source in the project has one (bls_ooh, college_scorecard, karpathy_ai_exposure, onet, cip_soc_crosswalk). @primary-agent must create this file during implementation and register it in `domain/manifest.yaml`. Should include: name, namespace, table, dedup_grain, fetch config (api_url template, fallback_path, user_agent), cache_dir, and authority/license/methodology comments. | @primary-agent creates `domain/sources/bea_rpp.yaml` during implementation. Not blocking. |
| 3 | ADVISORY | **Business glossary term IDs BT-098 and BT-099 need collision check.** Highest currently-allocated term ID in `governance/business-glossary.json` is BT-097. BT-098 and BT-099 are therefore free — no collision. The spec's pre-declared term IDs are valid. Noting this as PASS with an advisory for @data-steward to re-verify at allocation time in case other in-flight specs allocate intermediate IDs first. | @data-steward verifies BT-098/BT-099 still free immediately before allocating. |
| 4 | ADVISORY | **API key dependency introduces a runtime prerequisite.** The Bronze ingestor requires `BEA_API_KEY` in `.env` for the preferred path. Without the key, the ingestor falls back to a CSV that must be manually pre-downloaded to `data/raw/bea_cache/bea_rpp_2024.csv`. For CI/test environments (or fresh clones) this means either (a) the key must be in the test environment, or (b) the CSV cache file must be checked into the repo (~5KB, public domain — safe to commit), or (c) tests must mock the ingestor fetch. The spec does not state which strategy is preferred. | @primary-agent should decide and document: commit the CSV cache file to `data/raw/bea_cache/` (recommended — file is 5KB, public domain, eliminates the API dependency for CI/tests), and treat the BEA API as an optional refresh path. Not blocking, but should be resolved during implementation. |
| 5 | ADVISORY | **Stale-data risk depends on spot-check thresholds only.** The Bronze DQ rules include California (108.0-115.0) and Arkansas (84.0-90.0) spot checks to guard against stale data, but not all "known" 2024 values from the spec's reference table are DQ-enforced. Hawaii (110.0), DC (109.9), NJ (108.8), MS (87.0), IA (87.8), OK (87.8) are documented in the spec but not covered by DQ rules. The two existing spot checks are sufficient to catch wholesale data drift, but adding 2-4 more would provide stronger detection of partial corruption (e.g., only the top or only the bottom of the distribution shifts). | @dq-rule-writer may consider adding 1-2 more spot checks (suggest Hawaii and Mississippi) for redundancy. Not blocking — two spot checks plus range checks plus row count give reasonable coverage for a 51-row table. |
| 6 | ADVISORY | **API response schema not versioned in spec.** The spec documents the BEA API returns `BEAAPI.Results.Data` with fields `GeoFips`, `GeoName`, `TimePeriod`, `DataValue`, `CL_UNIT`, `UNIT_MULT`. If BEA changes their API response structure (historically stable, but not guaranteed), the ingestor breaks silently unless a schema assertion is added. | @primary-agent should add an explicit structural assertion in the ingestor (e.g., assert `BEAAPI.Results.Data` exists and is a list, and the first element has the expected keys) to fail loudly on API schema drift. Not blocking. |
| 7 | ADVISORY | **Metro-area filter rationale is preventive but unverified.** The spec says "Filter to state-level GeoFips only (2-digit codes 01-56, plus 11 for DC) — exclude metro areas if present". The BEA SARPP table with `GeoFips=STATE` parameter should already return only state-level rows, so the filter is belt-and-suspenders. It's a correct defensive filter but the phrasing "if present" signals uncertainty about the API response shape. | @primary-agent should verify during implementation whether the metro rows can appear with `GeoFips=STATE` and either (a) log a DQ warning if unexpected GeoFips codes appear, or (b) confirm the filter is never exercised and document it as defensive. |
| 8 | ADVISORY | **No retry/backoff specified for BEA API.** The spec says "If API call fails (no key, rate limited, timeout), fall back to reading CSV". This is a binary choice — one failed call triggers the fallback. For production robustness, a single retry with short backoff before falling back would be more resilient to transient network blips. For a 51-row weekly-at-most fetch, this is negligible risk. | @primary-agent may implement a single retry before CSV fallback. Not blocking — the fallback strategy is sound. |

---

## Spec Quality Assessment

### Strengths

1. **Precise success criteria.** Exactly 51 rows. Exactly the SARPP/LineCode=1/2024/GeoFips=STATE slice. No ambiguity about what "correct" means.
2. **Known reference values baked into DQ rules.** The California 108-115 and Arkansas 84-90 spot checks convert documented domain knowledge directly into automated guards. This is exactly how reference-table DQ should work.
3. **Graceful degradation.** API + CSV fallback + known source URLs means the ingest can succeed even if BEA is unreachable, so long as the cached CSV is present. The ~5KB size makes caching trivial.
4. **Clear scope boundary.** The spec is explicit that this Bronze table does NOT join to other Gold tables by SOC/CIP — integration is a query-time / frontend / MCP concern. This prevents scope creep into Silver/Gold during Bronze implementation.
5. **Honest about public-domain provenance.** License (U.S. Government Work) and update cadence (annual, February) are documented. No PII risk to assess — this is state-level statistical aggregate data.
6. **Realistic effort estimate.** 1 hour for Bronze ingest is plausible for a 51-row, well-understood source with a simple API. Matches prior small-source velocity.
7. **Business glossary terms pre-drafted.** BT-098 (Regional Price Parity) and BT-099 (Purchasing Power Multiplier) are defined in the spec with source attribution and derivation formulas, accelerating @data-steward's work.

### Observations (not defects)

1. **Spec is multi-zone (Bronze through MCP + stretch Boss).** This review only covers Bronze. Silver, Gold, and MCP sections were read for context but are explicitly out of scope and will be reviewed in separate pre-implementation runs. The spec's workflow ordering (step 8 @primary-agent builds Silver + Gold after models exist) means Silver/Gold implementation cannot begin until @semantic-modeler delivers the 3-stage models for `base.bea_rpp` and `consumable.regional_price_parities`.
2. **Spec name is Bronze-shaped but content is full-pipeline.** Same cosmetic observation as the prior `raw-ingest-karpathy-ai-exposure` review — the spec name implies Bronze-only scope but the content covers 4+ zones. Content is internally consistent; the name is cosmetic only.

---

## Cross-Reference Verification

| Check | Result |
|-------|--------|
| Spec file exists at expected path | PASS — `docs/specs/raw-ingest-bea-rpp.md` |
| Pipeline state file exists | PASS — `governance/pipeline-state/raw-ingest-bea-rpp-pipeline.json` (mode: greenfield) |
| Spec references correct Bronze zone | PASS |
| Agent workflow matches Brightsmith pipeline template | PASS — all mandatory Bronze agents present |
| Governance artifact paths follow project convention | PASS |
| No conflicts with existing tables | PASS — `raw.bea_rpp` / `bronze.bea_rpp` is new |
| No PII impact | PASS — state-level public statistical data |
| Business glossary term IDs (BT-098, BT-099) not already allocated | PASS — highest existing is BT-097 |
| Domain source YAML exists | FAIL — Advisory #2 (must be created during implementation) |
| Namespace convention matches existing sources | ADVISORY — Advisory #1 (spec says `raw.`, existing convention is `bronze.`) |
| Iceberg table grain declared | PASS — one row per geo_fips, dedup_grain [geo_fips] |
| Expected row count declared | PASS — 51 rows |

---

## Decision Rationale

This spec is **approved for Bronze implementation**. It is exceptionally well-scoped for its size — a 51-row reference table with a trivial transformation chain, clear provenance, and a strong set of DQ rules anchored in documented 2024 values. The spec demonstrates sound engineering judgment:

- Primary + fallback data acquisition paths are both specified
- DQ rules include both structural (row count, range, nulls) and semantic (known-value spot checks) guards
- Scope is explicitly bounded — no cross-source join ambition at Bronze
- Public-domain license removes any governance concern about redistribution
- No PII, no CDE complexity beyond the state FIPS join key
- Business glossary term collision check was run and cleared

The eight advisory items are all implementation-time concerns that @primary-agent can resolve during the Bronze build:

- **Advisory #1 (namespace drift)** — recommend `bronze.bea_rpp` to match the project's existing pattern. Trivial fix during yaml creation.
- **Advisory #2 (missing source YAML)** — standard boilerplate created at implementation time.
- **Advisory #3 (BT-098/099 collision)** — verified clear today; revalidate at allocation time.
- **Advisory #4 (API key / CI strategy)** — recommend committing the 5KB CSV cache as the canonical offline fallback.
- **Advisory #5 (additional spot checks)** — optional, the two existing spot checks are sufficient.
- **Advisory #6 (API schema assertion)** — defensive hardening, not a blocker.
- **Advisory #7 (metro filter phrasing)** — verify at implementation time.
- **Advisory #8 (retry/backoff)** — optional for a weekly-cadence source.

None of these rise to CHANGES REQUESTED or REJECTED. No P0 governance gap exists for the Bronze phase.

**REQUIRE_HUMAN_APPROVAL is TRUE.** This review is the governance reviewer's recommendation. The human owner should review before Bronze implementation begins.

**Implementation ordering note:** The Bronze ingest can begin immediately after human approval. Silver/Gold/MCP implementation is **out of scope for this review** and must wait for their own pre-implementation reviews plus @semantic-modeler's 3-stage data models for `base.bea_rpp` and `consumable.regional_price_parities`.

---

*Reviewed against: Brightsmith CLAUDE.md framework rules, futureproof-data CLAUDE.md project conventions, prior Bronze specs (raw-ingest-onet, raw-ingest-bls-ooh, raw-ingest-karpathy-ai-exposure), existing domain/sources/*.yaml conventions, current business-glossary.json state, and governance reviewer pre-implementation checklist.*
