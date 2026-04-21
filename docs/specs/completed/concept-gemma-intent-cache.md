# Spec: Gemma Intent Resolution with Student-Validated Cache

**Status:** SPIKE PENDING — Do not implement spec until CLI spike validates the approach
**Created:** 2026-04-12
**Author:** Jeff + Claude Desktop

---

## Concept

Replace static YAML major-to-CIP lookup with a self-improving system: Gemma resolves student intent at query time, students validate the mapping, confirmed mappings are cached for future students. The system gets smarter with usage.

## The Flow

1. Student types a major name on the school+major selection screen
2. Check cache for (normalized_input, unitid) → if hit, use cached mapping instantly
3. If miss → Gemma call with:
   - Student's typed input
   - School's available CIP codes (from Scorecard)
   - Full crosswalk CIP list with titles
   - Agent persona context (see below)
4. Gemma reasons through the options → suggests a CIP mapping
5. Student sees the *career outcomes* of the suggested mapping (not the CIP code) → "You said 'Deaf Education' — we found careers like Special Education Teacher (Deaf/Hard of Hearing), Sign Language Interpreter. Is this what you're studying?"
6. Student confirms → mapping saved to cache with provenance
7. Student redirects ("No, I meant audiology") → Gemma re-reasons with the additional context → new suggestion → student confirms or redirects again
8. Next student types same thing at same school → cache hit → instant, no Gemma call

## Gemma Agent Personas (for alias generation and intent reasoning)

- **@counselor-voice** — "Students come to me saying they want to 'work with deaf kids.' That's CIP 13.1003."
- **@student-voice** — "I want to do pre-med. Or maybe bio. Something with hospitals?"
- **@parent-voice** — "My daughter wants to study Physical Therapy. Is that the same as Kinesiology?"
- **@registrar-voice** — "CIP 51.2308 is Physical Therapy/Therapist. Students confuse it with 31.0505 Kinesiology. Different programs, different outcomes."

These personas inform Gemma's system prompt when resolving ambiguous inputs. Gemma considers how different audiences describe the same program.

## Cache Architecture

- **Cache key:** (normalized_input, unitid) — school-aware to handle "Data Science" mapping to different CIPs at different schools
- **Cache value:** resolved CIP code, crosswalk SOCs, Gemma's reasoning, confirmation count
- **Promotion threshold:** N confirmations (3? 5?) before a mapping is treated as trusted. Below threshold, Gemma still fires but the cached suggestion is presented first.
- **Provenance per entry:** which student query created it, Gemma model version, reasoning text, timestamp, confirmation count
- **TTL:** Entries expire on quarterly data refresh or when the CIP code no longer appears in the school's Scorecard data

## Seed Data

The existing 56 YAML entries (Business + Education families) bootstrap the cache as pre-validated mappings. These skip the confirmation threshold — they're human-curated. Expand to ~200-300 covering the most common majors before launch so Gemma only fires for the long tail.

## Adversarial Mitigations

1. **Confirmation threshold** — single student can't pollute the cache. Need N confirmations of the same mapping.
2. **Validate careers, not codes** — student sees "careers like Special Ed Teacher" not "CIP 13.1003." Harder to confirm garbage when you're confirming career outcomes.
3. **Gemma semantic validation** — periodic batch job checks cached mappings: "does 'pre-med' → CIP 51.1102 make semantic sense?" Garbage fails.
4. **Input sanitization** — reject obviously adversarial inputs before they reach Gemma.
5. **Admin review queue** — new mappings below confirmation threshold are flagged for review in school deployments (Tier 3).

## Drawbacks to Validate in Spike

- **Latency:** How long does Gemma take to resolve intent from a CIP candidate list? Acceptable for a one-time call at major selection?
- **Accuracy:** Does Gemma reliably pick the right CIP from a list of candidates? What's the error rate?
- **Ambiguity handling:** How well does Gemma handle genuinely ambiguous inputs ("I want to do business")?
- **School-specific CIP availability:** Can Gemma reason about which CIPs a specific school reports vs. the full crosswalk?
- **Cold start UX:** What does the student experience look like when Gemma fires vs. cache hit? Is the delay acceptable?
- **Redirect loop:** If the student says "no, not that," does Gemma converge or oscillate?

## Hackathon Demo Value

- **Visible Gemma capability:** Judge types an unusual major → watches Gemma reason through it → sees the resolution → confirms. The system learned.
- **Second student demo:** Same major → instant cached response. "The system got smarter from the first student."
- **Tier 3 / Ollama story:** School deploys locally → students build up a cache tuned to how *their* students talk about *their* programs. Different schools, different caches, same Gemma. Community-adaptive.
- **Video beat:** "Watch what happens when FutureProof encounters a major it hasn't seen before..."

## Relationship to CIP Intent Resolution Gold Product

If the spike validates, this replaces the static YAML pipeline entirely. The Gold data product (`consumable.cip_intent_resolution` from `gold-cip-intent-resolution.md`) becomes the *cache store* — governed, DQ-validated, with lineage. Instead of ingesting a human-curated YAML through Bronze, the Bronze source becomes the cache entries themselves, validated by students and verified by Gemma.

The existing spec (`gold-cip-intent-resolution.md`) should be held until the spike completes. If the spike works, the spec gets rewritten around the cache architecture. If the spike fails (Gemma too slow, too inaccurate, or the UX is awkward), fall back to the static YAML Gold product as designed.

## Spike Plan

Spike in `backend/cli.py`:
1. Student types a major → check a local dict cache → if miss, call Gemma with school's CIP list
2. Gemma returns suggested CIP + reasoning
3. Show student the career outcomes for that CIP → ask for confirmation
4. If confirmed → save to dict cache
5. If rejected → ask for clarification → re-call Gemma → repeat
6. Test: type the same major again → verify cache hit, no Gemma call
7. Log: Gemma latency, token count, accuracy of first suggestion

---

*Do not proceed to full spec until spike validates. This doc captures the concept so we don't lose it.*
