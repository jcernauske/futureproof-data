# FutureProof Data Sources — Verified Dossier

Compiled 2026-05-09 by code-walk through `src/raw/*.py`, `src/silver/*.py`, `src/gold/*.py`, `frontend/src/data/statExplanations.ts`, and `docs/reference/voice-guide.md`. Every source below is named with the same full-name-on-first-reference convention the app uses in its receipts (per the canonical "Receipts — data sources are NAMED" decision in the Set Your Course spec).

---

## The Ten Sources

| # | Source (full name on first reference, then acronym) | Taxonomy | Vintage | URL anchor in code | What it powers |
|---|---|---|---|---|---|
| 1 | **U.S. Department of Education College Scorecard** — Field of Study + Institution feeds | CIP, IPEDS | 2024 release (most recent) | `ed-public-download.app.cloud.gov` | ERN per-program earnings rank · ROI debt-to-earnings · net price · school catalog |
| 2 | **Bureau of Labor Statistics — Occupational Outlook Handbook (BLS OOH)** | SOC | current | `bls.gov/emp/tables/...` | GRW (10-year growth projection) · Ceiling boss · Market-Demand boss |
| 3 | **Bureau of Labor Statistics — Occupational Employment and Wage Statistics (BLS OEWS)** | SOC | 2024 national file (`oesm24nat`) | `bls.gov/oes/special-requests/oesm24nat.zip` | Per-career wage percentiles (10/25/50/75/90) — the newest layer, just shipped this branch |
| 4 | **Occupational Information Network (O\*NET)** — Tasks, Work Activities, Work Context, Related Occupations, Experience | SOC | Database 30.2 | `onetcenter.org/dl_files/database/db_30_2_text.zip` | Task-level work profiles · branch tree (career transitions) · Burnout boss · the O*NET layer of the RES blend |
| 5 | **National Center for Education Statistics CIP↔SOC Crosswalk** (CIP 2020 ↔ SOC 2018) | CIP × SOC | 2020/2018 | `nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx` | The bridge — every "what does this major lead to" query passes through this lookup |
| 6 | **Karpathy AI Exposure Scores** (open-source `github.com/karpathy/jobs`) | SOC | live repo | `raw.githubusercontent.com/karpathy/jobs/...` | RES (AI resilience) — Karpathy layer · Fight AI boss |
| 7 | **Anthropic Economic Index** (HuggingFace dataset `Anthropic/EconomicIndex`) | SOC | most recent release | `huggingface.co/datasets/Anthropic/EconomicIndex` | RES (AI resilience) — observed-exposure layer |
| 8 | **Bureau of Economic Analysis — Regional Price Parities (BEA RPP)** | FIPS state | 2024 | `apps.bea.gov/api/data/` | Cost-of-living adjustment · `compare_purchasing_power` MCP tool |
| 9 | **NCES Integrated Postsecondary Education Data System — Finance (IPEDS-Finance)** | IPEDS UNITID | Fiscal Year 2023 | `nces.ed.gov/ipeds/datacenter/data/F2223_F1A.zip` (and F2/F3) | AURA (Brand Gravity) — endowment-per-student layer |
| 10 | **U.S. Department of Education Equity in Athletics Disclosure Act (EADA)** | IPEDS UNITID | 2022–23 academic year | `ope.ed.gov/athletics/` | AURA (Brand Gravity) — athletic-budget layer |

There is also an **11th**, smaller feed (`gemma_ai_exposure_ingestor.py`) — a Gemma-derived AI exposure overlay. It exists in the pipeline but doesn't drive a user-facing stat directly; treat as out-of-scope for the data-sources screen unless a beat specifically calls for it.

---

## Aggregate scale claim

The voice guide and the video script both use **"700,000 rows of public data"** as the marketing-vetted scale claim. This is the only aggregate number that should appear on screen — anything more granular (per-source row counts) drifts as the pipeline updates and isn't worth maintaining for a 5-second beat.

> Source: `docs/reference/voice-guide.md` line 13 — *"The app has 700K rows of public data behind every number."*

---

## Taxonomy primer (for design — these acronyms WILL appear on screen)

- **CIP** — Classification of Instructional Programs (NCES). The taxonomy of college majors. Format: `XX.XXXX` (e.g., `52.1401` = Marketing).
- **SOC** — Standard Occupational Classification (BLS). The taxonomy of jobs. Format: `XX-XXXX` (e.g., `13-1161` = Market Research Analyst).
- **IPEDS** — Integrated Postsecondary Education Data System. The federal student-records system. Each institution has a unique `UNITID`.
- **FIPS** — Federal Information Processing Standards code. State-level geographic identifier.

---

## What groups together visually

For a single screen, the 10 sources break naturally into four categories — this matches how the app's Receipts surfaces group them:

| Cluster | Sources | What it tells the student |
|---|---|---|
| **Earnings & cost** | College Scorecard · BLS OEWS | "What you earn, what it costs" |
| **Career landscape** | BLS OOH · O\*NET · CIP↔SOC Crosswalk | "Where the job actually takes you" |
| **AI resilience** | Karpathy AI Exposure · Anthropic Economic Index | "How safe this is from automation" |
| **Institution & geography** | IPEDS-Finance · EADA · BEA Regional Price Parities | "What the school's name carries · what the dollar buys where you live" |

---

## What this screen sits between in the video

Per `docs/video/futureproof-video-script-v1.md`:

- **Predecessor (BEAT 6, 0:38–0:48):** *"The data to solve this actually exists — federal earnings, labor projections, task-level job data — 700,000 rows across five public sources. But it's incomplete, disconnected, and nobody's stitched it together for students."*
- **This screen (the visual for BEAT 6):** Shows the data sources cleanly. The voiceover says "five public sources" — but the verified count is 10. The script's "five" is approximate / outdated and should be updated to the real number, OR this screen should consolidate the 10 down to 5 visual clusters (the four-category grouping above gives 4; the script's "five" can be reached by splitting Earnings & Cost into separate Earnings/Cost cards, or by surfacing the CIP↔SOC Crosswalk as its own bridge cluster).
- **Successor (BEAT 7, 0:48–0:56):** *"That's where Gemma comes in. It bridges the gaps between sources, maps what a student types to real career paths, and keeps every analysis grounded in actual data — not guesses."* — Visual: data sources flowing into Gemma.

So the screen has **two jobs**:
1. **Show the receipts.** Make the federal-data backbone visible — judges scoring "Impact & Vision" need to see this isn't an LLM with vibes; it's an LLM on top of a real pipeline.
2. **Set up Gemma.** End in a state where the next beat ("Gemma bridges the gaps") feels like the natural next frame — the sources should appear messy / disconnected / scattered enough that "Gemma stitches them together" earns its moment.

---

## Files referenced

- `src/raw/*_ingestor.py` (13 ingestor files, 10 distinct upstream sources)
- `src/gold/*.py` (gold transformers — what each source becomes)
- `frontend/src/data/statExplanations.ts` (canonical short-form source attributions per stat)
- `docs/reference/voice-guide.md` (700K rows claim)
- `docs/video/futureproof-video-script-v1.md` (BEAT 6–7 voiceover and visual direction)
- `CLAUDE.md` (project-level Data Sources table)
