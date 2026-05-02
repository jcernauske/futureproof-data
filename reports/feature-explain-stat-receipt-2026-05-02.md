# Feature Report: Explain-Stat Receipt — Structured JSON Renderer (ERN)

**Spec:** `docs/specs/feature-explain-stat-receipt.md` (DRAFT v1.3 → COMPLETE)
**Branch:** `aura-stat`
**Shipped:** 2026-05-02
**Author:** Jeff + Claude Code (Opus 4.7, 1M context)

---

## Summary

Replaced the in-app ERN-explain spike's free-form Gemma markdown output with a server-validated structured-JSON receipt rendered by a dedicated React component. ERN-only in v1.0; the schema generalizes to ROI / RES / GRW for future specs (AURA explicitly out of scope per Decision 10 — needs an additive root-level provenance field).

**The trust contract:** Gemma writes the prose fields (`one_liner`, per-component `explainer`, `why_mix_paragraph`); the server stamps every numeric field (`score`, `math_line`, percentile values, dollar anchors, missing-reason strings, sources). Pydantic `extra="forbid"` + a sentinel-passthrough validator catch hallucination. JSON-mode is applied only on the synthesis turn of the tool loop (per-backend translation: OpenRouter `response_format` vs Ollama native `format`). Parse failure falls back to the existing markdown spike with the cached `tool_call_log` injected — no MCP re-fetch.

**The math reliability problem solved:** the spike rendered `"4.3/10"` when the formula `_round_half_up(1 + 9 × raw)` yields `2/10`. With server-side computation that failure mode is structurally impossible.

---

## Pipeline result

| Phase | Agent | Verdict | Notes |
|-------|-------|---------|-------|
| 1. Architecture review | @fp-architect + @genai-architect (parallel) | APPROVED after 2 iterations | v1.1 → CHANGES REQUESTED (8+7 conditions). v1.2 → 8/8 fp-architect resolved + 7/7 genai-architect resolved + 1 new genai concern. v1.3 → APPROVED. |
| 2. Design vision | @fp-design-visionary | §3 filled | 5 minor implementation flags, no spec conflicts. |
| 3. Implementation | Claude Code | Complete | 12 files; 1440 insertions, 105 deletions. |
| 4. Testing | @test-writer | 74 new tests, all green | Backend 1395 + Frontend 790, zero regressions. |
| 5. Design audit | @fp-design-auditor | CHANGES REQUIRED → RESOLVED in 5b | 16 FAIL items (7 P0 a11y + 9 P1 visual). All applied. |
| 6. Code review | @faang-staff-engineer | CHANGES REQUIRED → RESOLVED in 6b | 2 blockers + 4 serious + 1 moderate. All applied. |
| 7. Verification | @fp-builder | PASS-pending-smoke | Initial ruff fail (E501 in JSON template) auto-fixed in 7b via per-file ignore. mypy mis-attribution corrected: 0 spec-introduced mypy errors. |
| 8. Completion | This report | DONE | Spec status COMPLETE pending manual smoke. |

---

## Files changed (commit-level)

| Commit | Phase | Description |
|--------|-------|-------------|
| `49d18c9` | Pre-spec reshape + spike | Pentagon-stat-reshape (HMN→AURA) + ERN-explain markdown spike. Bundled because they touched overlapping files. |
| `58ea40a` | Pre-spec docs | pentagon-stat-explanation skill + surface index + this spec (DRAFT v1.0). |
| `3ffae80` | Spec v1.2 | Architecture-review CHANGES REQUESTED applied. |
| `88fab87` | Spec v1.3 | Sentinel-passthrough concern from genai-architect re-review. |
| `bb6c2e0` | Spec §3 | @fp-design-visionary filled the UI spec. |
| `098fb20` | **Phase 3** | Implementation: backend Pydantic models + ask_gemma JSON path + gemma_client per-backend kwarg + frontend Zod + new `<ExplainStatReceiptCard>` + GemmaChat dispatch. 1440 / 105. |
| `c46aae4` | **Phase 4** | 74 new tests across 3 backend files + 3 frontend files. 0 regressions. |
| `bf037c3` | **Phase 5b** | 16 design-audit fixes (border-default + rounded-[14px] + boxShadow + 44px score + percentile callout row + missing-data ◦— glyph + sr-only headings + slug-based source-pill testids + scale:0.985 entrance + motion.li wrapping). |
| `1b7aa79` | **Phase 6b** | 6 code-review fixes (B1 Zod fallback string + B2 effort labels + S1 tool_result_full + S2 halfway-effort line + S3 fallback task cancellation + S4 score_max stamp + M1 PLACEHOLDER tightening). |
| (this commit) | **Phase 7b** | ruff fixes (per-file E501 ignore for JSON template; F401/I001 auto-fix). mypy mis-attribution corrected. Status → COMPLETE. |

---

## Test coverage

- **Backend pytest:** 1399 passed in 5.5s. Net new: 58 tests (`test_ask_gemma_explain_receipt.py` ×48, `test_ask_gemma_explain_integration.py` ×6, `test_gemma_client.py` ×4).
- **Frontend vitest:** 790 passed in 15.7s. Net new: 16 tests (`ExplainStatReceipt.test.tsx` ×8, `menu.test.ts` ×7, `GemmaChat.test.tsx` ×1).
- **Frontend tsc:** clean.
- **Vite production build:** 903 modules, 1.7s.
- **Manual smoke:** DEFERRED to human run on both `INFERENCE_BACKEND=ollama` and `INFERENCE_BACKEND=openrouter`.

---

## Known follow-ups

1. **Manual smoke verification** on both backends before merge to main.
2. **Production parse-success-rate metric.** Filter `gemma.jsonl` records on `call_site == "explain_ern_receipt"`. Monitor for 2 weeks; consider removing the markdown spike fallback if rate stays >85%.
3. **ROI / RES / GRW receipt specs** — schema fits, each needs a worked example in SKILL.md + a per-stat label allowlist + a stat-specific appendix variant.
4. **AURA receipt spec** — needs one additive root-level `score_provenance: str | None` field. Decision 10 v1.2 documented this.
5. **Pre-existing mypy debt** — 69 errors in 18 unrelated files. Worth a separate `tech-debt-mypy-strict.md` spec.
6. **Frontend exhaustiveness check** — `GemmaChat.renderMessageWithTrace` lacks `assertNever` on `m.kind`. Phase 6 N5; deferred.

---

## What worked

- **Three review rounds.** Phase 1 (arch + genai), Phase 5 (design), Phase 6 (staff eng) each found real issues the test suite had not caught. Both audits found user-facing bugs in production-equivalent paths (`effort.capitalize()`'s `Working_hard` bug; the `[object Object]` leak path; the silent halfway-case effort suppression).
- **The Skill ↔ Spec ↔ Implementation triangle.** SKILL.md voice rules → spec §3 design + §4 contract → component implementation. Each layer was the binding contract for the next; nothing freelanced.
- **The Decision Log discipline.** 15 numbered decisions in §2 made every reviewer's "why isn't this X?" answerable from the spec. Decisions 10, 13, 14, 15 specifically were direct outputs of the architecture review and prevented churn in implementation.

## What hurt

- **fp-builder mis-attributed mypy errors.** A `git stash` round-trip was needed to confirm the 9 `[type-arg]` errors weren't actually new. Build-verification agents should baseline first.
- **One auditor agent ran while another was editing the same file.** Phase 1's parallel reviewers and the Phase 5 audit each appended to §5/§8 cleanly, but I had to retry one Edit due to a "file modified since read" race. Workflow lesson: serialize agents writing to the same spec section.
