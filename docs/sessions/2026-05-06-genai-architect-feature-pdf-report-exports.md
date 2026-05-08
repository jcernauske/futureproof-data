# Session Log — @genai-architect — feature-pdf-report-exports

**Session ID:** 2026-05-06-genai-architect-pdf-01
**Timestamp:** 2026-05-06 14:22
**Agent:** @genai-architect
**Spec:** `docs/specs/feature-pdf-report-exports.md`
**Stage:** DESIGN VISION — Gemma prompt + JSON schema review

---

## Scope

Review the `### Gemma System Prompt and JSON Schema` subsection written by
`@fp-copywriter` in §4 of the PDF report exports spec. Covers prompt
construction quality, JSON schema design, token budget, failure-mode coverage,
scoping/privacy, and dual-backend compatibility.

---

## Actions Taken

1. Read the full `### Gemma System Prompt and JSON Schema` subsection (lines
   1125-1278) including the `_SYSTEM` constant, `_user_prompt` template,
   failure-mode table, and token budget rationale.

2. Read §2 Decision Log entries #4, #5, #6, #7 for voice rules, RPG-language
   ban scope, and call-count decisions.

3. Read `AudienceQuestions` Pydantic model (lines 880-888) and
   `RPG_TERMS_FORBIDDEN_IN_PDF` frozenset (lines 986-996) to cross-check
   alignment between the system prompt forbidden list and the post-filter.

4. Read §3.11.4 static fallback questions to validate voice examples.

5. Read §3.11.5 data-coverage caveat copy to confirm no substitution-caveat
   conflict with the Gemma prompt.

6. Counted tokens in `_SYSTEM` using cl100k_base approximation (~295-315 tokens
   against the 300-token ceiling; noted Gemma SentencePiece adds ~5-12%).

7. Cross-referenced forbidden vocabulary between system prompt and
   `RPG_TERMS_FORBIDDEN_IN_PDF` — found two classes of gaps.

8. Appended full findings to §10 Discussion of the spec.

---

## Findings Summary

**STATUS: CHANGES REQUESTED** — 5 required changes, 3 advisory notes.

### Required Changes

**C1 — Remove bare `stat` from system prompt forbidden list** (`_SYSTEM`
line in `pdf_questions.py`). "stat" is overly broad and creates collateral
suppression of legitimate statistical language. The five named abbreviations
(ERN, ROI, RES, GRW, AURA) already cover the in-app UI labels. This is also
a misalignment: `RPG_TERMS_FORBIDDEN_IN_PDF` does not contain "stat" and
the post-filter IS word-boundary-anchored while the prompt is not.

**C2 — Add "level up" variants to `RPG_TERMS_FORBIDDEN_IN_PDF`** in
`pdf_copy.py`. The system prompt forbids "level up" but the post-filter
frozenset omits it. Gap in the belt-and-suspenders design.

**C3 — Add stat abbreviations to `RPG_TERMS_FORBIDDEN_IN_PDF`** in
`pdf_copy.py`. ERN, ROI, RES, GRW, AURA, HMN are forbidden by the system
prompt but absent from the post-filter. If Gemma leaks one, the regex filter
will not catch it.

**C4 — Replace `"..."` placeholder in schema example with concrete valid
JSON** (`_SYSTEM` output-format block). The `"..."` and bare `...` notation
is Python pseudocode, not valid JSON. Gemma in json-mode may emit the literal
"..." string. Replacement uses a one-element concrete example that also
models the audience-voice rule implicitly.

**C5 — Add `_BOSS_ADVISORY_LABEL` constant requirement and docstring note**
to `pdf_questions.py` spec for `_top_two_risks` / `_top_two_strengths`. These
helpers must emit advisory labels ("AI displacement risk") not raw BossId
strings ("ai") or in-app RPG display names ("Fight AI"). If this requirement
is not explicit in the spec, an implementor reading only `_user_prompt` will
make the wrong call.

### Advisory Notes

**A1** — `test_audience_caps_enforced` docstring should clarify that the cap
is 5 (Pydantic max) not 3 (Gemma ask). No spec text change required.

**A2** — Implementor must measure `_SYSTEM` token count with tiktoken before
shipping and document it in the module docstring. Gemma tokenizer runs ~5-12%
higher than cl100k_base; the prompt may be 315-340 Gemma tokens against the
300-token ceiling. If over, trim the "return empty array" closing paragraph.

**A3** — Add code-fence stripping before `json.loads()` in `pdf_questions.py`
to defend against OpenRouter occasionally wrapping JSON in ```json ... ```
fencing despite the "no code-fence" instruction.

---

## Decisions Made

- Approved the 0..3 no-filler license (over 1..3) as the correct design.
  Static fallbacks guarantee floor-of-1 per audience; Gemma returning []
  is strictly better than Gemma writing filler.

- Approved the defense-in-depth regex post-filter as appropriate, not
  overkill. `response_format="json"` guarantees JSON validity but not
  vocabulary compliance. For a non-negotiable (Decision #4) the three-layer
  architecture (system-prompt constraint + json-mode + post-filter) is correct.

- Approved the dual-backend design as written. The prompt is backend-agnostic;
  JSON-mode translation lives in `gemma_client.py` not the prompt. The
  explicit JSON mention in the system prompt satisfies OpenRouter's requirement
  for `response_format: {"type": "json_object"}`.

- Approved the scoping design. `_user_prompt` passes exactly five advisory
  fields; no PII, no raw scores, no RPG labels, no internal IDs.

---

## Artifacts Produced

- §10 Discussion entry appended to
  `docs/specs/feature-pdf-report-exports.md`
- This session log:
  `docs/sessions/2026-05-06-genai-architect-feature-pdf-report-exports.md`

---

## Handoff

CHANGES REQUESTED back to `@fp-copywriter`:
- C1: Edit `_SYSTEM` constant to remove `stat` from forbidden list.
- C4: Edit `_SYSTEM` output-format block to replace pseudocode schema example
  with concrete valid JSON example.

CHANGES REQUESTED to `@fp-copywriter` or implementor (spec-level):
- C2, C3: Edit `RPG_TERMS_FORBIDDEN_IN_PDF` frozenset in the §4 spec block
  for `pdf_copy.py` to add "level up" variants and stat abbreviations.
- C5: Add `_BOSS_ADVISORY_LABEL` constant requirement and docstring note to
  the §4 `pdf_questions.py` spec block.

After C1-C5 are applied, the subsection is ready for IMPLEMENTATION handoff.
