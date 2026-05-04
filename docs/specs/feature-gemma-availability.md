# Feature: Gemma Availability / Outage Mitigation (PLACEHOLDER)

## Status: TODO

> **This is a placeholder, not a spec.** It exists to capture a new architectural risk introduced by `feature-set-your-course.md`: Gemma is now on the critical path of the product, not a decorative overlay. A Gemma outage (OpenRouter 502, Ollama crash, rate-limit burst during a judge demo) becomes a product outage, and unlike the old narrative-layer Gemma, we have no cheap deterministic fallback for *reasoning*. The real spec must pick a strategy and implement it before submission.

---

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-19 |
| Last Updated | 2026-04-19 (placeholder created; not promoted) |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 0.0 (stub) |
| Deadline pressure | 2026-05-18 (Kaggle submission) — demo must be judge-proof |
| Blocks | Shipping `feature-set-your-course.md` to the Kaggle submission demo |
| Related Specs | `docs/specs/feature-set-your-course.md` (primary consumer — its resolution path + chip flow + community-suggestions surface all depend on Gemma being reachable), `docs/specs/feature-learned-alias-cache.md` (DEFERRED — but its JSONL idea partially resurfaces here as the community-suggestions fallback), `docs/specs/feature-receipts.md` (graceful-degradation messaging still has to cite what sources we COULD reach when Gemma can't; outage mode doesn't excuse unsourced claims), `docs/specs/feature-chat-guardrails.md` (outage fallbacks must respect the same voice + safety rules), `docs/specs/completed/cloud-gemma-deployment.md` |
| Mockup reference | `docs/specs/design/set-your-course-mockup/index.html` — the scenarios this spec protects. Scenarios 2 (streaming), 8 (chip debug stream), 9 (chip resolved), 10 (community suggestions visible) are all fragile to Gemma outage. The graceful-degradation mode (option (d)) needs its own mockup treatment when this spec is promoted. |

---

## §1 The Risk

Before Set Your Course, every Gemma call had a static deterministic fallback:
- Boss narration failed → a pre-written boss line.
- Guidance failed → a pre-written coaching sentence.
- Skill recs failed → a pre-written static list.

That works when Gemma is **decoration**. It does not work when Gemma is the **reasoning engine**. Set Your Course has no static substitute for:
- Mapping free-text major → CIP (the YAML short-circuit is retired from the resolution path entirely in the reinforcement-loop design).
- Reconciling crosswalk inconsistencies via tool-call-driven chip debug traces.
- Explaining why a resolution shifted mid-chip flow.
- Classifying career feasibility into the 5 modes (direct_hit / crosswalk_quirk / adjacent_reachable / school_gap / genuinely_impossible).

So now: **any Gemma outage = a product outage**, with no graceful degradation. On a 3-minute Kaggle video, an OpenRouter 502 is not a bug report — it's the entire submission. The severity is worse than the earlier scoping anticipated because the reinforcement-loop design no longer has YAML as a "just in case" fallback on the resolution hot path — it's Gemma all the way down.

---

## §2 Candidate Mitigations

The real spec picks one or a combination. Options, roughly ordered by strength:

### (a) Break-glass YAML fallback

When the resolution Gemma call fails, fall back to `major_lookup.lookup_major` (the YAML short-circuit retired from the main flow in the reinforcement-loop design). The 56 hand-curated entries catch the most common demo inputs. Requires keeping the YAML *file* in place during the transition even after the code path is removed — a "break-glass env var" (`INTENT_YAML_BREAKGLASS=true`) re-enables the short-circuit only on Gemma failure.

**Pros:** cheapest. No new state. Already tested code path.
**Cons:** only covers 56 inputs. Silent CIP substitution without Gemma reasoning is back to the pre-Gemma UX. No conversation, no crosswalk explanation, no community suggestions. Feels like a degraded product. Also: the reinforcement-loop design's eventual step is to DELETE `major_lookup.py` post-demo — the break-glass keeps it around for at least one more cycle.

### (b) Community-suggestions fallback

The reinforcement-loop design already maintains `data/reference/student_corrections.jsonl` with an in-memory aggregate behind `community_suggestions.get_suggestions(unitid, input_normalized)`. On Gemma resolution failure, consult this surface: if the (unitid, input_normalized) key has ≥1 cacheable suggestion, serve the top one as the resolution. Student sees a reduced experience — no streaming reasoning, no feasibility debug trace — but the career preview still renders from a real student-validated path.

**Pros:** reuses state we're already maintaining for the reinforcement loop. No new file, no new service. Covers exactly the inputs students have corrected before — which tends to be the hardest cases (the ones Gemma gets wrong). Zero student-facing latency on hit.
**Cons:** cold entries still fail. First-visitor to any (unitid, input) has no crowd signal; if Gemma also fails, we're in graceful-degradation territory (option d). Also: this makes the community log load-bearing for availability, not just UX — raises the stakes on guardrails and poisoning defense.

### (c) Local Ollama as hot fallback when OpenRouter fails

Run both backends. Route to OpenRouter by default (for the cloud deployment / demo), fall back to local Ollama on OpenRouter failure.

**Pros:** the strongest story — "we run on any hardware, and we prove it by failing over to local mid-demo." Actually demonstrates the local-first thesis.
**Cons:** demo machine must have Ollama running + the model pulled. Adds complexity. Two backends = two sets of prompt tuning considerations (temperature=0+seed behavior is similar but not identical across backends).

### (d) Graceful degradation with explicit messaging

When Gemma is unavailable, show the student a minimal resolution ("we matched your input to CIP X — we're running lean right now and can't explain why, but here are the careers") and log the failure. No chat, no correction, proceed to reveal.

**Pros:** honest. Avoids faking success.
**Cons:** reveals the outage to the judge. Doesn't save the demo.

### (e) Pre-warm demo inputs before live demo

Before the video is shot or the live demo is run, script a pre-warm pass that calls Gemma for every input we expect a judge to try. Hit the cache (from (b)) on demo day.

**Pros:** demo-specific insurance, very cheap.
**Cons:** doesn't help real students, only the submission. Still needed for production.

### Recommendation direction (pre-real-spec, updated for reinforcement-loop design)

Probably **(a) + (b) + (e)** for hackathon, in order of fallback attempt:

1. **(e) Pre-warm** — before the video, run every demo input through the system so corrections are seeded and Gemma's response is cached in the community-suggestions aggregate.
2. **(b) Community-suggestions fallback on Gemma failure** — if the (unitid, input) has a cacheable suggestion, serve it. Demo survives the most common input paths.
3. **(a) YAML break-glass** — env-gated re-enable of `major_lookup.lookup_major` only when both Gemma AND community suggestions fail. Keeps the 56 hand-curated cases as a last-resort net. This is the reason `backend/app/services/major_lookup.py` is not deleted until post-demo.
4. **(d) Graceful degradation with messaging** — if all of the above miss, honest tone: "We're running lean right now; here's the closest match we have, and here's how to try again." Never fake a result.

**(c) Local Ollama as hot fallback** stays as post-hackathon work if we have a multi-machine demo setup.

---

## §3 Specific Failure Scenarios the Real Spec Must Address

1. **OpenRouter 429 rate-limit** during a live demo (judge types the same input 3 times). Already handled by `gemma_client` retry; the concern is user-facing perceived latency spike.
2. **OpenRouter 5xx** (provider-wide outage). No retry policy helps. Need fallback.
3. **Ollama process crashed** on the demo machine. Need fallback or restart automation.
4. **Cold model on Ollama** (first query after reboot takes ~30s). Need pre-warm.
5. **Network outage** on the demo laptop at the venue. Ollama continues, OpenRouter dies; need (c) or pre-warm.
6. **`.env` misconfiguration** — `OPENROUTER_API_KEY` not set, `INFERENCE_BACKEND=ollama` but Ollama not running. Hard-fail today; need a sane error state.
7. **Model returns malformed JSON** on a specific prompt + seed combo. Already handled with `bad_json` logging; confirm the outage-mitigation path isn't silently swallowing real prompt bugs.
8. **Judge stress-test: same input 20× in 10 seconds.** Rate-limit both backends. Need request coalescing or a short in-memory idempotency cache.

---

## §4 Observability Requirements

When the real spec lands, it must ship with:
- A `logs/gemma_failures.jsonl` or equivalent capturing every failure + fallback-path-taken.
- Stdout warnings during demo if fallback fires (quiet, but visible in a terminal tail).
- A smoke-test script (`scripts/gemma_health_check.py`) that exercises resolution + chat + tool-calling and exits non-zero if anything fails. Run before every recorded demo.

---

## §5 Out of Scope for This Placeholder

Everything. This is a stub. The real spec picks the strategy.

---

## §6 Discussion

```
[2026-04-19] Created alongside submission-kaggle-narrative.md placeholder
after product scoping locked in that Gemma is core (not decorative). The
founder's exact ask: "we need to mitigate the risk of openrouter outage
somehow (yaml fallback, cache fallback, etc.)"

The YAML-disable spec (docs/specs/bugfix-disable-intent-yaml-regression.md)
intentionally keeps the YAML file in place — only the short-circuit is
disabled. That preserves (a) as a zero-new-code mitigation.

The parked learned-alias-cache spec's JSONL shape is partially applicable
to (b) — but the DEFERRED cache had a learning loop + acceptance threshold
+ cross-conflict resolution. This mitigation would cut all that and keep
only the "last successful resolution per input" lookup. Simpler, narrower,
and justified by outage safety rather than narrative.

Block condition: cannot ship the Set Your Course demo to the Kaggle video
recording without picking SOMETHING from §2. Option (a) alone is
acceptable if it's the cheapest path to demo safety.
```
