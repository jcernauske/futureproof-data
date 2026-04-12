# FutureProof — Spec Backlog

**Last updated:** 2026-04-11
**Deadline:** May 18, 2026

---

## Sequencing Key

| Priority | Meaning |
|---|---|
| **P0 — HACKATHON CRITICAL** | Must ship by May 18. Blocks demo credibility or core product loop. |
| **P1 — HACKATHON BONUS** | Ships if time allows after P0 + frontend + video are done. Strengthens submission. |
| **P2 — POST-HACKATHON** | Product roadmap. Not attempted before May 18. |

---

## P0 — Hackathon Critical

### 1. CIP Disaggregation Fix
**Status:** Spike complete, spec not written
**Spike findings:** `docs/specs/spike-intent-substitution.md`
**What it does:** Fixes the bug where IU Marketing students see Construction Manager as a career path. Implements student-intent CIP substitution: a YAML lookup table maps "Marketing" → CIP 52.14. When a school reports only broad CIP (e.g., 52.01), the system substitutes the specific CIP's crosswalk SOC mappings while keeping the school's broad-CIP earnings for ERN/ROI. ~150-250 row YAML file. Bypass logic: if the school already reports the specific CIP, skip substitution entirely.
**Why P0:** Judges will search top schools + popular majors. Many will hit this bug. Credibility killer if unfixed.
**Depends on:** Nothing — can build immediately.
**Estimated effort:** 4-6 hours (lookup table curation + MCP tool update + tests)

### 2. Student Career Path Override
**Status:** Spec not written
**What it does:** Frontend text input where a student adds a missing career path ("you missed Product Manager"). System searches `consumable.occupation_profiles` for the matching SOC, pulls the full pentagon + boss scores + career branches from governed pipeline data. Gemma contextualizes the addition: "common path" vs "stretch" vs "data doesn't support this connection." Never refuses to show data — frames plausibility honestly.
**Why P0:** Safety net for CIP disaggregation edge cases. Also a strong demo moment for the video — shows the product empowering the student, not dictating to them.
**Depends on:** CIP Disaggregation Fix (the override handles cases substitution misses).
**Estimated effort:** 3-5 hours (MCP tool for SOC search + Gemma prompt engineering + frontend input)

---

## P1 — Hackathon Bonus

### 3. Career Pathfinding
**Status:** Spec not written
**What it does:** Triggered when a student's override targets a role with no common hop from their major (e.g., Art Education → CEO). Gemma computes skill/experience gaps using O*NET task deltas between the student's starting position and the target role. Shows realistic intermediate hops, each with stats and requirements. "No common path from Art Ed to CEO, but here's what you'd need to build along the way."
**Why P1:** Powerful demo moment but not blocking core loop. The override itself works without pathfinding — pathfinding just makes the "stretch" response richer.
**Depends on:** Student Career Path Override (pathfinding is the stretch-path handler within the override flow).
**Estimated effort:** 6-8 hours (Gemma prompt engineering + O*NET task delta computation + frontend rendering)

### 4. Gemma AI Exposure Re-Score
**Status:** Spec written (`docs/specs/gemma-ai-exposure-rescore.md`, BACKLOG)
**What it does:** Replaces Karpathy's Gemini Flash scores with Gemma 4-generated scores using O*NET task-level data. Scores at the task level, not occupation level. Coverage jumps from 342 → 798 occupations. Produces an A/B comparison (Karpathy vs. Gemma) for the Kaggle writeup.
**Why P1:** Strengthens Technical Depth score. "We didn't just use someone else's scores — we used Gemma to re-score every occupation." Also doubles RES/AI coverage in the pentagon.
**Depends on:** Core pipeline complete (it is). Only trigger after frontend + video storyboard are done.
**Estimated effort:** 8-12 hours (prompt engineering + batch run + pipeline ingest + A/B report)

### 5. Notable Alumni Enrichment
**Status:** Spec not written
**What it does:** Agentic search pipeline that prefetches notable alumni for suppressed school+major combos (where `has_earnings=false`). Gemma batch-searches notable alumni, results ingested through Brightsmith as a governed data source (`consumable.notable_alumni`, keyed `unitid × cipcode`). Reframes missing earnings data as "buyer beware + inspiration" rather than a dead end. Works offline for Tier 3 Ollama deployments.
**Why P1:** Turns the 64% earnings suppression rate from a weakness into a product feature. Also demonstrates Gemma doing pipeline-level data enrichment (Technical Depth). But the product works fine without it — suppressed earnings just show a "data unavailable" message.
**Depends on:** Nothing — can build anytime. But lower priority than CIP fix and frontend.
**Estimated effort:** 6-10 hours (Gemma batch search + Brightsmith pipeline + MCP tool)

### 6. Show Your Work (Data Lineage UI)
**Status:** Spec not written
**What it does:** Frontend feature where every data point is tappable, showing its source dataset, field, DQ rules passed, confidence tier, and whether it's observed vs. estimated. Raids Brightforge (Brightsmith's sister project) for lineage UI components.
**Why P1:** Differentiates from other hackathon entries. Builds trust. But it's a frontend feature that requires the frontend to exist first.
**Depends on:** Frontend screens built.
**Estimated effort:** 4-8 hours (lineage data already exists in governance artifacts — this is UI rendering)

---

## P2 — Post-Hackathon

### 7. Course Catalog Crawler
**Status:** Spec not written
**What it does:** Brightsmith ingestor that pre-crawls 200-500 school websites via Gemma. Extracts the full ecosystem of opportunities: minors, certificates, electives, clubs, business fraternities, research programs, one-off courses. Gold zone grain: `unitid × opportunity_type`. Powers the "How do I fix this?" feature on risk assessments — when a student's build has a weakness, the product shows specific opportunities at their school that would address it. Each opportunity tagged with stat impact.
**Why P2:** High value but massive scope. Requires web crawling infrastructure, Gemma extraction, and a new Gold data product. Not feasible in hackathon timeline.
**Estimated effort:** 20-40 hours

### 8. Tier 3 Data Update
**Status:** Spec not written
**What it does:** One-button update mechanism for school self-hosted deployments. Hyena Studios runs Brightsmith centrally, publishes Gold zone data bundles. School hits an update button, pulls the latest packaged data files. No pipeline runs on-site, no Brightsmith at the school. "Connect once a quarter, hit update, disconnect."
**Why P2:** Deployment infrastructure, not product functionality. The hackathon demo can show the Tier 3 concept without the update mechanism.
**Estimated effort:** 8-12 hours

### 9. Native AI Exposure Scoring
**Status:** Spec not written
**What it does:** Full rebuild of Karpathy's work natively with Gemma. Scores at the O*NET task level (not occupation level). Produces multi-dimensional scores: automation risk, augmentation potential, demand elasticity. Runs through Brightsmith DQ pipeline with full governance and lineage. Batch job via Ollama.
**Why P2:** The Gemma Re-Score spec (#4) is the hackathon-scoped version of this. This is the production-grade version with richer scoring dimensions. Back of backlog — only after everything else.
**Estimated effort:** 20-30 hours

---

## Completed Specs (Reference)

| Spec | Zone | Status |
|---|---|---|
| `raw-ingest-college-scorecard.md` | Bronze | COMPLETE |
| `silver-base-college-scorecard.md` | Silver | COMPLETE |
| `gold-career-outcomes-college-scorecard.md` | Gold | COMPLETE |
| `raw-ingest-bls-ooh.md` | Bronze | COMPLETE |
| `silver-base-bls-ooh.md` | Silver | COMPLETE |
| `gold-occupation-profiles-bls-ooh.md` | Gold | COMPLETE |
| `raw-ingest-onet.md` | Bronze | COMPLETE |
| `silver-base-onet.md` | Silver | COMPLETE |
| `gold-onet-profiles.md` | Gold | COMPLETE |
| `crosswalk-cip-soc.md` | Silver | COMPLETE |
| `gold-futureproof-engine.md` | Gold | COMPLETE |
| `gold-futureproof-engine-addendum-cip-fix.md` | Gold | COMPLETE |
| `raw-ingest-karpathy-ai-exposure.md` | Bronze→Gold+MCP | COMPLETE |
| `raw-ingest-bea-rpp.md` | Bronze | COMPLETE |
| `silver-base-bea-rpp.md` | Silver | COMPLETE |
| `gold-regional-price-parities.md` | Gold | COMPLETE |
| `mcp-bea-rpp.md` | MCP | COMPLETE |
| `mcp-futureproof-core.md` | MCP | COMPLETE |
| `fix-gld-op-039.md` | Gold | COMPLETE |

## Completed Spikes (Reference)

| Spike | Finding |
|---|---|
| `spike-broad-cip-prevalence.md` | 23.5% of rows are broad XX.01 CIPs. Systemic across families. |
| `spike-cip-override-table.md` | Override table only covers 26 broad-only Business schools. IU isn't one — it reports both. Too narrow. |
| `spike-gemma-query-filter.md` | Gemma filtering can't work — the marketing SOCs aren't in the candidate set to begin with. Dead end. |
| `spike-cip-hierarchy-fallback.md` | Hierarchy fallback unsafe — only 22% SOC overlap between 52.01 and 52.14. SOC sets are complementary, not nested. |
| `spike-intent-substitution.md` | Student-intent CIP substitution works. Lookup table + blended earnings = correct career paths. Validated end-to-end. |

---

## Non-Spec Work Remaining (Hackathon)

| Workstream | Status | Estimated Effort |
|---|---|---|
| Frontend (8 screens, React/Vite) | NOT STARTED | 1-2 weeks |
| Gemma agent integration (function calling) | NOT STARTED | 1 week |
| Midjourney character assets | NOT STARTED | 2-3 days |
| Character card renderer | NOT STARTED | 1-2 days |
| Ollama local deployment verification | NOT STARTED | 1-2 days |
| Video production (3 min, story-driven) | NOT STARTED | 3-5 days |
| Submission package (README, writeup, repo, media) | NOT STARTED | 2-3 days |

---

## Framework Fixes (Brightsmith Repo, Post-Hackathon)

| Issue | Description |
|---|---|
| `domain_loader.py` multi-table support | Requires singular `table:` but O*NET uses `tables:` (plural). Crashes on load. |
| `_load_zone_registry()` pipeline shape | Expects flat pipeline shape but futureproof-data uses nested list-of-steps. Blocks `/bs:serve`. |

---
