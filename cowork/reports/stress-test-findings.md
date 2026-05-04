# FutureProof Stress Test Log
- **Started:** 2026-05-03 23:43 UTC
- **Tester:** Claude Cowork (simulating 16-year-old students)
- **App:** http://localhost:5173
- **Scope this session:** Tier 1 — Students 1–5 (20 builds)

---

<!-- Student sections will be appended below as each student completes their 4 builds. -->

## Pre-flight notes
- Builds counter started at **7** before this session (preexisting state from prior tests).
- After Build 1 of Student 1, counter jumped from 7 → **9** (+2). Only one "Spec my build" click. `[SUS]` — possible double-save, or a phantom build from an earlier failed click on a different tab.
- Profile screen on each new tab generates a fresh persona name, so persona name varies between tabs. Not a bug for this run, but worth flagging: a single-session multi-tab user could end up with multiple personas in one profile.

---

## Student #1: The Indiana Kid
- **Profile:** Lively Snug Bunny / 🐰 / Home: IN (state set on /profile, "Let's go →")
- **Vibe:** TBD — collecting after all 4 builds.

### Build 1: Indiana University-Bloomington + "business" → Chief executives
- Effort: balanced (slider value 2/4) | Loans: 50% (slider value 2/4)
- Pentagon: ERN=10 ROI=3 RES=7 GRW=6 AURA=6
- Bosses: AI=D Loans=D Market=W Burnout=D Ceiling=L (verdict: "VULNERABLE BUILD" — 1W/3D/1L)
- Cost 4yr: $109,444 (avg net price $61,368) | Starting salary: $63,371 | Median: $206,420
- Modeled debt at 50%: $54,722 (program median debt: $19,500 — flagged as "significantly above")
- CIP: 52.01 Business/Commerce, General | SOC: 11-1011
- Weirdness:
  - `[WRONG NUMBER]` Salary percentiles are nonsensical: "25th: $38,515 · 75th: $49,674" sit underneath "Median salary $206,420". 75th cannot be below median. Numbers look like early-career graduate earnings from Scorecard glued to a BLS median label.
  - `[CONFUSING]` Starting salary $63,371 is *higher* than the displayed 75th percentile $49,674 — a 16-year-old would absolutely notice and not understand which number is "real".
  - `[SEARCH FAIL]` School search for "Indiana University Bloomington" returned "No schools found"; only "Indiana University" matched. The canonical name in the DB uses a hyphen ("Indiana University-Bloomington"). Real students will type the space form.

