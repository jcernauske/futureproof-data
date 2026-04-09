# Lineage Tracker Audit Trail: raw-ingest-onet

**Agent:** @lineage-tracker
**Spec:** docs/specs/raw-ingest-onet.md
**Timestamp:** 2026-04-07T22:00:00Z
**Lineage File:** governance/lineage/raw-ingest-onet-20260407T220000Z.json

## Scope

Captured OpenLineage events for 5 of the 7 tables specified in raw-ingest-onet. The spec defines 7 tables, but only 5 were ingested in this run (Career Changers Matrix and Career Starters Matrix were not part of the ingestion batch provided).

## Events Captured

| # | Job Name | Output Table | Row Count | Column Lineage Entries | Source File |
|---|----------|-------------|-----------|----------------------|-------------|
| 1 | raw.ingest-onet-occupations | raw.onet_occupations | 1,016 | 7 | Occupation Data.txt |
| 2 | raw.ingest-onet-task-statements | raw.onet_task_statements | 18,796 | 11 | Task Statements.txt |
| 3 | raw.ingest-onet-work-activities | raw.onet_work_activities | 73,308 | 17 | Work Activities.txt |
| 4 | raw.ingest-onet-work-context | raw.onet_work_context | 297,676 | 18 | Work Context.txt |
| 5 | raw.ingest-onet-related-occupations | raw.onet_related_occupations | 18,460 | 9 | Related Occupations.txt |

## Tables NOT Captured (Not Ingested)

- **raw.onet_career_changers** (Career Changers Matrix.txt) -- ingestor class exists (OnetCareerChangersIngestor) but table was not part of the ingestion batch
- **raw.onet_career_starters** (Career Starters Matrix.txt) -- ingestor class exists (OnetCareerStartersIngestor) but table was not part of the ingestion batch

These will require lineage events when they are ingested.

## Decisions and Observations

1. **Input namespace:** Used `onetcenter.org` as the input namespace since the data originates from the O*NET Center. Each source file gets a distinct input dataset name following the pattern `onet-database-30.2.{file-slug}`.

2. **Row counts match user-provided actuals:** The row counts in runtimeMetrics match the actual ingestion counts provided (1,016 / 18,796 / 73,308 / 297,676 / 18,460), not the spec estimates (~886 / ~19,000 / ~71,000 / ~49,000 / ~17,000). Notable that raw.onet_work_context has 297,676 rows vs. the spec estimate of ~49,000 -- this is because Work Context includes multiple scale/category combinations per element per occupation.

3. **Derived field (is_primary):** The `is_primary` field in raw.onet_related_occupations is classified as DERIVED because it is computed from the Relatedness Tier column (with index fallback), not a direct copy from the source. Two input fields are listed in the column lineage.

4. **relatedness_tier field:** The ingestor code includes a `relatedness_tier` field that is not in the original spec schema (spec says `is_primary` only). This was added during implementation for O*NET 30.2 compatibility. Captured in lineage as-is from the actual code.

5. **Shared ZIP architecture:** All 5 ingestors share a common OnetBaseIngestor base class that handles ZIP download and caching. The ZIP is downloaded once; each subclass extracts its specific file. This is documented in the job facets via sourceCodeClass.

6. **Transformation types:** All bronze zone ingests are DIRECT (type coercion from TSV strings to Iceberg types) except: `is_primary` (DERIVED from Relatedness Tier + Index logic) and the four framework metadata fields (ingested_at, source_url, source_method, load_date) which are DERIVED by BaseIngestor.

7. **O*NET metadata flags preserved:** The spec requires recommend_suppress and not_relevant to be preserved as-is in Bronze. The lineage correctly documents these as DIRECT copies with notes about Silver zone filtering.
