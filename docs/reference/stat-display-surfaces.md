# Stat Display Surfaces — Reference Index

> **⚠️ Reshape in flight (2026-05).** `docs/specs/pentagon-stat-reshape.md` is mid-implementation on this branch. **HMN ("Human Edge") has been removed**; its O*NET signal folds into a new **blended RES**. The freed 5th-axis slot is now **AURA ("Brand Gravity")**, an institution-level score from `consumable.institution_aura`. The `StatKey` type has already cut over to `"ern" | "roi" | "res" | "grw" | "aura"`. This index has been rewritten for the post-reshape shape; until the reshape lands fully, verify file references against the spec before acting.
>
> **Final pentagon: ERN, ROI, RES (blended), GRW, AURA.**

**Purpose.** Every place in the FutureProof app where a user sees one of the five pentagon stats (ERN, ROI, RES, GRW, AURA) and could plausibly want an "Ask Gemma to explain this" affordance. Built so a future feature (universal "explain this stat in context") can be wired up without missing a surface.

**Scope.** Frontend display surfaces + the export surfaces (Wrapped renderer, share frames). Source-of-truth scoring lives in `src/gold/` and `backend/app/services/stat_engine.py` — see `.claude/skills/pentagon-stat-explanation/SKILL.md`.

**Last audited.** 2026-05-02 (branch `aura-stat`). Re-audit any time a new screen, card, or overlay is added that displays a stat number, stat name, stat color dot, or stat-derived delta. The `feedback_stat_blast_radius_check` memory enforces this on every stat change.

**Companion docs.**
- `.claude/skills/pentagon-stat-explanation/SKILL.md` — voice rules and copy structure for stat explanations.
- `frontend/src/data/statExplanations.ts` — single source of truth for stat metadata (name, abbreviation, color, blurb).
- `frontend/src/components/build-results/bossData.ts` — `STAT_INFO` long-form definitions, `STAT_COLORS` map.
- `backend/app/services/ask_gemma.py` — `_STAT_ALIAS` map for chat scope chips ("Asking about: Earning Power" / "Asking about: Brand Gravity").
- `docs/specs/pentagon-stat-reshape.md` — the in-flight spec driving the HMN→AURA cutover.

---

## Legend

| Symbol | Meaning |
|---|---|
| ✅ | "Ask Gemma to explain this" already wired up |
| ⚠️ | Stat is shown but no explain affordance — **candidate for the new feature** |
| 📦 | Behind-the-scenes display (LLM-facing context, not a user surface) |
| 🎨 | Marketing/landing — explain affordance not appropriate here |

---

## 1. Build Results screen — `/build/:id`

The primary stat-display surface. Pentagon + legend + boss-fight bands.

### 1a. Pentagon legend (the stat list with bars and "?" buttons)
- **File:** `frontend/src/screens/BuildResultsScreen.tsx:688-773`
- **Component:** Inline list rendering each `STAT_EXPLANATIONS` entry with score, color dot, name, blurb, "?" info button, and `<StatInfoPopover>`.
- **What user sees:** Five rows. Each row: dot · `ERN` · "Earning Power" + one-line blurb · `?` · `10/10`.
- **Affordance:** ✅ "?" button opens `StatInfoPopover` with long-form definition + "Ask Gemma about this" CTA. Wired via `handleAskStat` (`BuildResultsScreen.tsx:73`).
- **"✦ Explain this to me" trigger (ERN, ROI, RES, GRW rows):** Always visible on these four rows regardless of score. Dispatches `[explain-this:{STAT}]` sentinel via `handleExplainStat`. AURA stays ⚠️ until the AURA spec ships. See `docs/specs/feature-explain-stat-receipt-roi-res-grw.md`.

### 1b. Pentagon chart itself
- **File:** `frontend/src/components/PentagonChart.tsx`
- **What user sees:** SVG pentagon with five labeled axis points (ERN/ROI/RES/GRW/AURA) and the score number under each label.
- **Affordance:** ⚠️ **None.** Hovering an axis only highlights the corresponding legend row. Clicking the axis label (or the dot at the axis tip) is **not currently** an explain trigger.
- **AURA missing-data state.** When `stats.aura === null` the AURA vertex draws as an **open ring** (no fill, `text-muted` stroke) at the outer perimeter, the label reads `AURA —` (em-dash), and the polygon fill stops short of that vertex. Any explain affordance attached to this axis must remain tappable in this state and route to the AURA missing-data popover (§1g below).
- **Note:** Per user input, axis label hover/click is a strong candidate for an inline explain affordance.

### 1c. Boss-fight stat deltas (per BossBand)
- **File:** `frontend/src/components/build-results/BossBand.tsx:76-80`
- **What user sees:** Each boss outcome surfaces stat deltas (`delta_ern`, `delta_roi`, etc.) — e.g., "ERN +2 RES −1" tags showing how applied skills shifted stats during the fight.
- **Affordance:** ⚠️ **None on the stat tags themselves.** The boss has its own "Ask why" button (`BossBand.tsx:66`), but the individual stat-delta tags within a fight don't open a stat explainer.

### 1d. Skill cards (in skill pool) — stat deltas
- **File:** `frontend/src/components/build-results/SkillStatBadge.tsx`
- **What user sees:** Skill chips like "Internship at Google → ERN +2, RES +1".
- **Affordance:** ⚠️ **None on the badges.** The skill itself can be asked about (`handleAskSkill` in `BuildResultsScreen.tsx:102`), but not the stat label inside the badge.

### 1e. PathCard — alternate path stat preview
- **File:** `frontend/src/components/build-results/PathCard.tsx:13-65`
- **What user sees:** Path card showing all five stats as horizontal bars (`StatBarRow`).
- **Affordance:** ⚠️ **None.** No info button, no popover, no Ask Gemma trigger.

### 1f. FinancesCard — ROI receipt
- **File:** `frontend/src/components/build-results/FinancesCard.tsx:138`
- **What user sees:** ROI score appears inside a "receipt" of cost-vs-earnings math (debt-to-earnings ratio, financed DTE, ROI label).
- **Affordance:** ⚠️ **None.** This is the only place ROI is shown alongside the actual debt/earnings inputs that produce it — a strong candidate for an inline explain affordance.

### 1g. AURA missing-data popover (post-reshape)
- **File:** `frontend/src/components/build-results/StatInfoPopover.tsx` + `bossData.ts` `STAT_INFO.aura` (post-reshape).
- **When it shows:** Student taps the `?` next to AURA on a build whose institution has no `consumable.institution_aura` row (~10% of unitids — schools with neither IPEDS-Finance nor EADA athletics coverage).
- **What user sees:** Standard AURA popover body, then an **appended line in `font-body` 13px `text-muted`** with 8px top margin: *"Not enough institutional data for {school name} to score this yet."*
- **Affordance:** ⚠️ **Partial.** The popover renders, the "Ask Gemma about this" button is still active, but Gemma has no AURA score to explain. Any "explain this" affordance must detect `stats.aura === null` and either suppress itself or route to a "why doesn't my school have AURA?" explainer (different intent than the standard explainer — closer to a coverage explanation).
- **Hard constraint** (per memory `feedback_no_substitution_caveat.md`): no banner, no toast, no card-edge tint. The em-dash on the vertex (§1b) and the appended sentence in this popover are the **only** missing-data sentences in the UI.

### 1i. ExplainStatReceiptCard — structured explainer-receipt (ERN ✅, ROI ✅, RES ✅, GRW ✅, AURA ⚠️)
- **File:** `frontend/src/components/menu/ExplainStatReceipt.tsx`
- **When it shows:** Student clicks "✦ Explain this to me" on any stat row (ERN, ROI, RES, GRW) → slide-in chat opens → backend's JSON-mode path dispatches via `_STAT_EXPLAIN_REGISTRY` → per-stat postprocessor returns an `ExplainStatReceipt` payload → `GemmaChat`'s renderer dispatches on `kind: "receipt"` → this component renders. AURA is gated on its separate spec (`feature-explain-stat-receipt-aura.md`).
- **What user sees per stat:**
  - **ERN:** Gold rail, 2 components (60% school rank + 40% career rank), math line `0.6 × A + 0.4 × B → score N/10`, effort-line footnote when `effort != "balanced"`.
  - **ROI:** Green rail, 1 component (100% DTE bucket, `value_pct=null` by design — no percentile callout, only `anchor_dollars`), math line `$X / $Y = Z.ZZ → ROI score N/10`.
  - **RES:** Blue rail, 2 components (50% AI exposure + 50% human-essential, both with `value_pct` populated from raw 1-10 row scores × 10), math line `0.5 × A + 0.5 × B → score N/10`.
  - **GRW:** Red rail, 1 component (100% employment-change band, `value_pct=null` by design — no percentile callout, only `anchor_text`), math line `+X.X% employment change → GRW score N/10`.
- **Affordance:** ✅ **This IS the explain-this-stat affordance.** The card itself doesn't carry a follow-up "ask Gemma" button (the user already asked). Subsequent free-form chat in the same panel routes through the standard prose handler.
- **Backend null-score short-circuit (ERN only, post-bugfix):** Before the JSON-mode tool loop runs, if `build.career.stats.ern is None`, both `chat_ask` and `chat_ask_stream` return a server-built receipt with `score=None` and per-input `missing_reason` lines. No Gemma call, no MCP re-fetch. See `docs/specs/bugfix-explain-stat-trigger-null-score-guard.md`.
- **Spec:** `docs/specs/feature-explain-stat-receipt.md` (ERN, COMPLETE); `docs/specs/feature-explain-stat-receipt-roi-res-grw.md` (ROI/RES/GRW).
- **Schema:** Pydantic `ExplainStatReceipt` in `backend/app/models/api.py`; Zod mirror in `frontend/src/types/chat.ts`.

### 1h. RES + AURA stat tutorial cards (post-reshape, first-build only)
- **File:** Stat tutorial overlay (location TBD by reshape implementation; spec §3 calls for a card per stat shown only on first build).
- **What user sees:** Tutorial overlay with five cards (one per stat). The reshape **rewrites the RES card** (new copy describes the blend) and **replaces the HMN card with an AURA card** ("Brand Gravity"). Each card has a body (~155 chars) + a source line.
- **Affordance:** ⚠️ **None.** This is one-time onboarding copy. Not a candidate for the explain affordance — the tutorial *is* the explain affordance.

---

## 2. Future / Tree screen — `/future/:buildId`

Branching career tree, with the build's pentagon as a root anchor and stat filters in the rail.

### 2a. Build pentagon (rail anchor)
- **File:** `frontend/src/screens/FutureScreen.tsx:122-126`
- **What user sees:** The build's pentagon stats are passed into the tree as the comparison root (`{ ern, roi, res, grw, aura }`). Note: AURA is institution-level and constant across every node in the tree (same school = same AURA), so AURA delta is always 0 in the comparison strip — the strip should consider hiding the AURA row entirely.
- **Affordance:** ⚠️ **None on the rail anchor itself** (depending on layout — verify in browser).

### 2b. SelectedNodeCard — branch destination stats
- **File:** `frontend/src/components/tree/SelectedNodeCard.tsx:60-65`
- **What user sees:** When a tree node is clicked, the rail card shows that destination's full pentagon (`ern, roi, res, grw, aura`) and computes deltas vs. the root. `delta_aura` is always 0 by spec invariant (Decision 5 in pentagon-stat-reshape) — AURA is institution-level, branches don't shift it.
- **Affordance:** ⚠️ **None per stat.** The card has Ask Gemma options for the *node*, not for individual stat values within the card.

### 2c. MiniCompareStrip — root vs. selected delta strip
- **File:** `frontend/src/components/tree/MiniCompareStrip.tsx:69-78`
- **What user sees:** Inline strip showing `delta` for pay (median wage), AI resilience (RES), and growth (GRW). The strip lives next to the SelectedNodeCard.
- **Affordance:** ⚠️ **None.** Each delta row could plausibly get a "?" or context-menu trigger.

### 2d. StatFilterRow — filter chips (stat labels, not values)
- **File:** `frontend/src/components/tree/StatFilterRow.tsx:14-20`
- **What user sees:** Chips like "AI-resilient" / "High-growth" used to filter the tree. Stat *names*, not *values*.
- **Affordance:** ⚠️ **Marginal.** Could explain what "AI-resilient" means as a filter — but this is filter UX more than stat copy. Lower priority.

### 2e. BossFilterRow — boss outcome filters (stat-derived)
- **File:** `frontend/src/components/tree/BossFilterRow.tsx`
- **What user sees:** Chips for "Survives AI", "Survives Market", "Survives Burnout" — each backed by a stat threshold.
- **Affordance:** ⚠️ **None.** Same low-priority note as 2d.

### 2f. PathRarityBadge — rarity tier badges
- **File:** `frontend/src/components/tree/PathRarityBadge.tsx`
- **What user sees:** Badge on tree nodes indicating how unusual a path is (computed from stat composition).
- **Affordance:** ⚠️ **None.** This is rarity, not a stat per se, but it's stat-derived.

---

## 3. Menu screen — `/menu` (or `/builds`)

Library of saved builds + side-by-side compare view.

### 3a. BuildCard with MiniPentagon
- **File:** `frontend/src/components/menu/BuildCard.tsx:82` → `frontend/src/components/menu/MiniPentagon.tsx`
- **What user sees:** Each saved build card shows a mini-pentagon thumbnail with all five stats.
- **Affordance:** ⚠️ **None.** Card opens the build, but the mini-pentagon itself isn't interactive for stat explanation.

### 3b. CompareView — overlay pentagon (multi-build)
- **File:** `frontend/src/components/menu/CompareView.tsx:200-204` → `frontend/src/components/menu/PentagonOverlay.tsx`
- **What user sees:** Multiple builds' pentagons overlaid; user can hover/highlight one at a time.
- **Affordance:** ⚠️ **None on stat axes.** The compare view has its own Ask Gemma entry, but it's whole-comparison-scoped, not per-stat.

### 3c. CompareView — stat-row table
- **File:** `frontend/src/components/CompareSchoolsPanel.tsx:734, 748, 897, 902`
- **What user sees:** Table comparing schools by ERN, ROI side by side.
- **Affordance:** ⚠️ **None.** Each column header is a strong candidate for an inline explain trigger ("What is ERN?").

### 3d. CharacterCard — stat label legend
- **File:** `frontend/src/components/menu/CharacterCard.tsx:12-16`
- **What user sees:** A legend with color-coded chips for each stat name (ERN/ROI/RES/GRW/AURA).
- **Affordance:** ⚠️ **None.** Direct candidate — these chips are already labeled with stat names.

### 3e. RiskHeadlineCard / CompareWinners / CompareProsCons
- **Files:** `frontend/src/components/menu/RiskHeadlineCard.tsx`, `CompareWinners.tsx`, `CompareProsCons.tsx`
- **What user sees:** Narrative cards that reference stat outcomes (e.g., "Stronger AI Resilience").
- **Affordance:** ⚠️ **None.** Narrative copy mentions stats but doesn't link to definitions.

---

## 4. Horizon mockups (interactive design previews)

Reachable from `/mockups` showcase — these are demonstration views, not part of the main user flow but still public.

### 4a. ChapterBookMockup
- **File:** `frontend/src/components/horizon/ChapterBookMockup.tsx:219, 242, 488`
- **What user sees:** Horizontal "chapter book" layout listing five-stat readouts at each timeline checkpoint.
- **Affordance:** ⚠️ **None.**

### 4b. HorizonStripMockup
- **File:** `frontend/src/components/horizon/HorizonStripMockup.tsx:211, 451`
- **What user sees:** Strip layout, same data shape.
- **Affordance:** ⚠️ **None.**

---

## 5. Career card (post-build career picker context)

### 5a. CareerCard — stat deltas vs. anchor
- **File:** `frontend/src/components/CareerCard.tsx:49`
- **What user sees:** Career options before commit-to-build show stats with optional anchor deltas (selected-vs-current).
- **Affordance:** ⚠️ **None per stat.** Card has full-card Ask Gemma in some flows, but not per-stat.

---

## 6. Save / Wrapped screen — `/save` or `/wrapped`

### 6a. Wrapped renderer — final stat readout
- **Backend file:** `backend/app/services/wrapped_renderer.py:86`
- **What user sees:** Shareable summary card; includes the build's final pentagon stats.
- **Affordance:** ⚠️ **None.** Output is a static image / PDF — explain affordance not feasible here. **Skip.**

### 6b. Wrapped HTML templates (post-reshape)
- **Files:** `backend/templates/wrapped/*.html` + `wrapped_renderer.py`'s `_STAT_NAMES`, `_STAT_COLORS`, `_STAT_CONTEXT` (lines ~77-99) and template-context emit (line 254 — `"stat_aura": stats.aura` post-reshape).
- **What user sees:** Same as 6a — final stat readout in the share frame. Listed separately because the reshape requires mechanical renames in templates: `{{ stat_hmn }}` → `{{ stat_aura }}`, label `"HMN"` → `"AURA"`. Grep before editing: `rg 'stat_hmn|\bHMN\b' backend/templates/`.
- **Affordance:** ⚠️ **None.** Static export. **Skip.**

---

## 7. Landing page — `/` (logged-out)

### 7a. HeroSection — sample pentagon
- **File:** `frontend/src/components/landing/HeroSection.tsx:40`
- **What user sees:** Illustrative pentagon with sample stats in the hero.
- **Affordance:** 🎨 **Skip.** Marketing surface — explain affordance is out of place. The HowItWorksSection on the same page does the explaining job.

### 7b. ReceiptPanelArt
- **File:** `frontend/src/components/landing/ReceiptPanelArt.tsx:53`
- **What user sees:** Decorative receipt naming "Earning Power".
- **Affordance:** 🎨 **Skip.**

### 7c. HowItWorksCardArt — BossRowArt, PentagonArt
- **File:** `frontend/src/components/landing/HowItWorksCardArt.tsx`
- **What user sees:** Decorative art tiles.
- **Affordance:** 🎨 **Skip.**

---

## 8. Gemma-facing context (LLM internal)

### 8a. boss_fights.py — stat lines
- **File:** `backend/app/services/boss_fights.py:81-92`
- **What it powers:** Strings injected into the boss-fight Gemma prompt so the LLM can reference stats by name.
- **Affordance:** 📦 **Out of scope** — this is what the LLM consumes, not what the user sees.

### 8b. ask_gemma.py — stat scope handler
- **File:** `backend/app/services/ask_gemma.py:110-116, 753-770`
- **What it powers:** When a user clicks "Ask Gemma about this stat", this builds the context block (drivers: median earnings, percentile, etc.).
- **Affordance:** 📦 **Already wired** — this is the existing handler that any new "explain this stat" affordance should route into.

### 8c. ChatScope schema — `kind: "stat"`
- **What it powers:** Frontend → backend contract for stat-scoped chat. Each stat-explain affordance must dispatch:
  ```ts
  { kind: "stat", build_ids: [build.build_id], target_id: "ERN" | "ROI" | "RES" | "GRW" | "AURA" }
  ```
- **Reference call site:** `frontend/src/screens/BuildResultsScreen.tsx:73-85`. Reuse this handler shape for any new surface.

### 8d. ERN explain-this-stat spike (in-app spike, not spec'd)
- **File:** `backend/app/services/ask_gemma.py` — `_ERN_EXPLAIN_OPENER`, `_ern_explain_appendix`, gated branches in `chat_ask` and `chat_ask_stream`.
- **What it powers:** When the frontend dispatches the sentinel opener `[explain-this:ERN]` with `target_id == "ERN"`, the backend swaps in a structured-explanation appendix (four-section template, mandatory tool calls to `get_career_paths` + `get_occupation_data`, percentile gloss rule, temperature 0). A leak stripper (`_HELPER_LEAK_RE` in the same file) keeps any `[helper: ...]` scratchpad blocks from reaching the user.
- **Affordance:** ✅ **Wired for ERN only** via `BuildResultsScreen.tsx` "✦ Explain this to me" link (`handleExplainErn`). If the spike works, a proper spec lands after the pentagon-stat-reshape wraps; until then ROI/RES/GRW/AURA do not have this affordance.

### 8e. `get_institution_aura` MCP tool (post-reshape)
- **File:** `src/mcp_server/futureproof_server.py` (new tool, post-reshape per spec Decision 8).
- **What it powers:** Single-keyed lookup against `consumable.institution_aura` for AURA's score, basis (`aura_score_basis`), coverage tier, and version. Returns the full row plus governance metadata via `attach_governance`. Called by `stat_engine.compute_pentagon` (server-side, once per build) AND addable to the chat tool allowlist if/when an AURA explainer wants to "show the receipts."
- **Affordance:** 📦 **Backend tool — not user-visible directly.** But any future "Explain AURA" affordance will rely on this tool for receipt rendering, so it belongs in the index.

---

## Audit checklist for the "Ask Gemma to explain this stat" feature

When wiring up the new affordance across surfaces, work through this list. Each ⚠️ above represents one row of work.

### Tier 1 — Direct stat values shown to user
- [ ] **1b** Pentagon chart axis labels (BuildResultsScreen)
- [ ] **1f** ROI inside FinancesCard receipt
- [ ] **2b** SelectedNodeCard pentagon (Future screen)
- [ ] **3a** BuildCard MiniPentagon (Menu)
- [ ] **3c** CompareSchoolsPanel column headers
- [ ] **5a** CareerCard stat row

### Tier 2 — Stat deltas (derived, but stat-named)
- [ ] **1c** BossBand stat-delta tags
- [ ] **1d** SkillCard stat badges
- [ ] **2c** MiniCompareStrip delta rows

### Tier 3 — Stat-name labels (no value, just the name)
- [ ] **3d** CharacterCard legend chips
- [ ] **2d** StatFilterRow filter chips (lower priority)
- [ ] **2e** BossFilterRow chips (stat-derived, lower priority)

### Tier 4 — Mockups + horizon (cosmetic / preview)
- [ ] **4a** ChapterBookMockup
- [ ] **4b** HorizonStripMockup
- [ ] **1e** PathCard StatBarRow

### Tier 5 — AURA-specific (post-reshape)
- [ ] **1g** AURA missing-data popover (~10% of unitids — needs a different intent than the standard explainer; route to a "why doesn't my school have AURA" answer)
- [ ] **1h** Stat tutorial cards (rewrite RES card for the blend, replace HMN card with AURA — this is onboarding copy, not an explain affordance)

### Skip
- **6a** Wrapped renderer image (static export)
- **6b** Wrapped HTML templates (static export — but the `stat_hmn → stat_aura` mechanical rename is still mandatory at reshape cutover)
- **7a–7c** Landing page (marketing)

### When wiring an affordance, every site must:
1. Resolve to one of the five `StatKey` values (`"ern" | "roi" | "res" | "grw" | "aura"`).
2. Dispatch the `{ kind: "stat", build_ids, target_id }` chat scope (Section 8c above).
3. Generate a chip label using the stat's plain name (`STAT_MAP[key].name`), not the abbreviation — the alias map in `ask_gemma.py:110` enforces this.
4. Have an `aria-label` of the form `"Ask Gemma about {stat name}"` (e.g., `"Ask Gemma about Earning Power"`) — never `"Ask Gemma about ERN"`.
5. Visually use `STAT_COLORS[key].text` for the trigger's accent color, so the affordance reads as belonging to that stat.
