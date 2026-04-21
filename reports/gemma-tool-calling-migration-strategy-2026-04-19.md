# Feature: Migrate Gemma Call Sites from Pre-Inject to MCP Tool-Calling

## Status: IN PROGRESS — row 0 shipped, rows 1-5 deferred

> Row 0 (chip dispatch) shipped via `feature-chip-dispatch-mcp-tool-calling.md` on 2026-04-20. This is now a real spec tracking the remaining migration work.
>
> **Key finding from row 0:** Pre-inject is genuinely better for the remaining call sites. Their data needs are deterministic and pre-injection wins on latency, reliability, and cost. Rows 1-5 should stay on pre-inject indefinitely unless measurement shows otherwise.

---

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-19 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 0.0 (stub) |
| Surfaced during | Session on 2026-04-19 (`docs/convos/2026-04-19-gemma-core-pivot.md`) |
| Related Specs | `docs/specs/feature-set-your-course.md` (already tool-call-first for chip routing — Tier P0 row 0 of §2), `src/mcp_server/futureproof_server.py` (the underutilized tool surface), `docs/specs/submission-kaggle-narrative.md` (tool-calling on local Ollama is a named demo beat), `docs/specs/feature-receipts.md` (every migrated call site MUST populate `sources_used` and the prompt MUST cite per the acronym spell-out rule — migration and receipts ship together per call site) |
| Mockup reference | `docs/specs/design/set-your-course-mockup/index.html` — **Scenario 9** shows the chip debug trace resolved state with a visible tool-call indicator; this is the demo-money beat the migration protects. Every migrated call site should produce an analogous visible tool-call moment on its own surface when that spec lands. |

---

## §1 The Architectural Inconsistency

We built:
- Brightsmith Bronze → Silver → Gold zones with data contracts + governance.
- A DuckDB Gold-zone warehouse at `data/futureproof.duckdb` with eight consumable tables.
- An MCP server at `src/mcp_server/futureproof_server.py` exposing Gold-zone data as eight Gemma-callable tools (`get_career_paths`, `get_occupation_data`, `get_ai_exposure`, etc.).

We then wired the runtime so that ~90% of Gemma calls work by:
1. Backend Python queries DuckDB directly.
2. Formats the results as bulleted strings.
3. Interpolates the strings into a `_SYSTEM_PROMPT` template via `.format()`.
4. Sends the prompt to Gemma.
5. Gemma autocompletes over the injected blob.

The MCP server's tool-calling surface is effectively bypassed by the only app that was supposed to use it.

---

## §2 Priority Order (Post-Hackathon Migration)

Migration is **sequenced**, not all-at-once. Each tier should be a separate PR so we can pause, measure, and adjust per-backend tool-call reliability before committing the next.

### Tier P0 — Ship during hackathon (load-bearing for the flagship demo)

| # | Service | Current pattern | Tool-call upgrade | Why P0 |
|---|---------|----------------|-------------------|--------|
| 0 | **`set_your_course.py::handle_chip_dispatch`** (NEW, per `feature-set-your-course.md`) | N/A — new service | Tool-call-first from day one. Gemma actively searches the crosswalk/careers data and classifies each candidate into one of 5 feasibility modes. This is the flagship tool-calling moment in the entire product. | **Non-negotiable.** The reinforcement-loop design depends on this. If tool-calling isn't working in this path by ship, the flagship doesn't ship. |
| 1 | `boss_fights.py::narrate_one` | Pre-inject boss stats + occupation row + AI exposure row | Gemma calls `get_occupation_data(soc)` + `get_ai_exposure(soc)` itself, reasons, narrates | **Demo headline #2.** If the boss-narration spec drafts before 2026-05-18, it MUST be tool-call-first (cross-ref from `submission-kaggle-narrative.md`). If it doesn't draft in time, this is the first migration post-hackathon. |
| 2 | `guidance.py::generate_guidance_async` | Pre-inject full build result | Gemma calls `get_career_paths(unitid, cip)` + relevant branches itself | "Gemma's Take" is the post-reveal flagship narrative. Grounding it in live tool calls is a significant UX + narrative upgrade. |

### Tier P1 — Next quarter after hackathon

| # | Service | Current pattern | Tool-call upgrade | Why P1 |
|---|---------|----------------|-------------------|--------|
| 3 | `career_tiering.py::tier_careers` | Pre-inject careers list, single-shot classification | Gemma queries the full list + `get_ai_exposure` per SOC, tiers with reasoning | Tier placement becomes explainable per-row ("this is common because..."), not a black-box labeling. |
| 4 | `skill_recs.py` | Pre-inject career profile | Gemma calls `get_task_breakdown(soc)` from O*NET | Recs cite specific O*NET tasks by name — "because this job does X 60% of the time, learn Y." |

### Tier P2 — Opportunistic

| # | Service | Current pattern | Tool-call upgrade | Why P2 |
|---|---------|----------------|-------------------|--------|
| 5 | `skill_pool.py` | Pre-inject career profile | Gemma calls `get_task_breakdown(soc)` | Secondary surface. Nice-to-have parity with skill_recs after P1 is settled. |

### Leave on pre-inject (no migration)

| Service | Reason |
|---------|--------|
| `intent._call_gemma_intent` | Pre-inject fits small, deterministic context well. The injected data (school CIPs + crosswalk CIPs) is computable once and cached. Tool-calling would add round trips without adding grounding since the data is already exhaustive for the decision. |
| `career_pick_qna.ask` | Chip surface is already narrow; each chip has a canned prompt with specific pre-fetched data. Matches pre-inject's strengths. |
| `school_lookup._gemma_resolve_major` | Narrow fallback path that only fires when YAML + exact-match both miss. Not on the hot path; migration ROI low. |

---

## §3 Hackathon Strategy (Recommended)

---

## §4 Hackathon Strategy (Recommended)

- **Don't do a full migration in the 29 days before 2026-05-18.** Scope risk.
- **Do insist that any new flagship Gemma surface is tool-call-first.** `feature-set-your-course.md` already is. When the boss-narration spec is drafted (PM's #2 priority), it should be tool-call-first too.
- Outcome: the **two headline Gemma moments in the demo** (unified screen + boss narration) both showcase tool-calling on local Ollama. Judges see the MCP server doing what it exists to do.
- Guidance, skill recs, career tiering, and skill pool stay on pre-inject for the hackathon. Migrate per the P0 → P1 → P2 sequence in §2.

---

## §5 Scope Hints for the Real Spec (Post-Hackathon)

When someone picks this up properly, think about:

1. **Tool-call reliability per backend.** OpenRouter's `google/gemma-4-26b-a4b-it` handles function calling well. Ollama's `gemma4:e4b` may not. Spec needs per-backend testing + fallback to pre-inject if a backend's tool-calling flakes.
2. **Token budget ceilings.** A rogue Gemma tool-call loop can blow budget. Per-call max-tool-calls cap (probably 3–5) + total-token cap per session.
3. **Streaming + tool-calling composition.** Set Your Course already does this for the chip-routing prompt. Establish the canonical pattern (stream prose → pause on tool call → execute → resume streaming → finalize) as a reusable helper in `gemma_client.py`.
4. **Cache friendliness.** Same tool-call with same arguments should memoize within a request; DuckDB is fast but 10 identical queries in one narration are still wasteful.
5. **Observability.** Every tool call already lands in `logs/gemma.jsonl` (via the prompt + response log). Consider a dedicated `logs/mcp_tool_calls.jsonl` that captures `{tool_name, args, result_summary, latency_ms, called_from}` for easier analytics than JSONL-of-blobs.
6. **Error surfaces.** Gemma calls `get_school_programs("Indiana University XYZ")` and the tool returns empty. Does the service report the empty result to Gemma? Say so plainly? Silently fall through? Spec picks a convention.
7. **Backward compat for the half-migrated state.** During the transition, some call sites are tool-calling and some are pre-inject. The shared prompt-log schema must accommodate both without rewriting historical logs.
8. **MCP server extension surface.** Four tools the migration exposes demand for but don't yet exist: `get_careers_for_cip(cip4) -> [SOC]`, `get_family_siblings(cip4) -> [CIP]`, `is_cip_offered_at(unitid, cip4) -> bool`, `get_peer_schools(unitid, k) -> [unitid]`. Probably worth adding incrementally rather than all-at-once.

---

## §6 Out of Scope for This Placeholder

Everything concrete. This is a stub. The real spec, when written, will define scope.

---

## §7 Discussion

```
[2026-04-19] Created after the founder observed: "it seems weird that we've
built this beautiful pipeline of bronze/silver/gold products, built MCP
servers, and then just pass text?"

The observation is right. The MCP server exists precisely so Gemma can
navigate structured Gold-zone data as a reasoning agent, not so the
backend can bypass it and hand-feed Gemma pre-selected context.

Current runtime uses pre-inject because it was the MVP path and because
Gemma-on-Ollama tool-calling maturity was uncertain. Both reasons are
still partially valid — but the cost is that we've quietly degraded
Gemma from "reasoning engine" to "template autocompleter" for the
majority of call sites.

Hackathon-honest recommendation: don't do a full migration now. Do
insist that the two headline demo surfaces (Set Your Course chip
routing + boss narration) are tool-call-first. That's enough to
prove the architecture works and to showcase it on-stage. Everything
else migrates after May 18 when scope pressure eases.
```
