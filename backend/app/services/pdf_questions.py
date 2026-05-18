"""Audience-question generation for PDF Report Exports.

See docs/specs/feature-pdf-report-exports.md §4 ``pdf_questions.py``.

Single scoped Gemma call returning all 3 audience arrays in JSON mode.
Falls back to static copy on every transport failure, malformed
response, schema violation, or forbidden-vocabulary leak. Every code
path emits exactly one ``logs/gemma.jsonl`` record (architect G3).

Token budget for ``_SYSTEM`` measured at ~280 tokens via
``tiktoken cl100k_base`` (see module docstring for the latest
measurement before merge — A2 from genai-architect §10).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re

from app.models.api import (
    AudienceQuestion,
    AudienceQuestions,
    GemmaPath,
)
from app.models.career import Build
from app.services import gemma_client
from app.services.locale import AppLocale, normalize_locale
from app.services.pdf_copy import (
    BOSS_ORDER,
    FORBIDDEN_IN_GEMMA_OUTPUT,
    boss_advisory_label,
    contains_forbidden_term,
    risk_level_for_boss,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Static fallback copy (§3.11.4).
# ---------------------------------------------------------------------------

STATIC_COLLEGE_MANDATORY: tuple[str, str] = (
    "Which majors at {school} most often lead graduates into {career}?",
    "How can I augment this major with the suggested skills above — through "
    "coursework, clubs, or internships you already offer?",
)

STATIC_COLLEGE_FALLBACK: str = (
    "What outcomes data do you publish for this program — median earnings "
    "one year out, employment rate, average debt at graduation?"
)

# Conditional 3rd mandatory question — only appended when the build's
# ERN and ROI both came back null. Mirrors the InsufficientDataBanner the
# student saw on the build screen, so they walk into the college conversation
# already knowing why they're asking.
STATIC_COLLEGE_MISSING_EARNINGS: str = (
    "Federal earnings data isn't published for your {program} program. "
    "How many students graduate from it each year, and what share take "
    "federal loans? Do you track post-graduation outcomes internally?"
)

STATIC_PARENTS_FALLBACK: tuple[str, ...] = (
    "If the loan numbers on page 1 are accurate, can the family adult "
    "carry that monthly payment alongside everything else after I graduate?",
    "Whose career did you watch up close growing up — and what about it "
    "would you want for me, or want to spare me from?",
)

STATIC_YOURSELF_FALLBACK: tuple[str, ...] = (
    "Will I still want to be doing this work in 10 years if the day-to-day "
    "looks like the O*NET task profile on page 1?",
    "Am I picking this major because it interests me, or because it's "
    "familiar — and would I know the difference yet?",
)


# Locale-keyed static fallbacks. Spanish + Arabic mirror the English
# voice (candid, concrete, action-verb-first for audience-facing rows,
# "Will I" / "Am I" first-person for ask_yourself). When Gemma is
# unavailable / off / malformed for an ar or es render, these are
# what prints — so they need to read like an advisor actually wrote
# them in that language, not like a machine-translated tooltip.
_STATIC_COLLEGE_MANDATORY_BY_LOCALE: dict[AppLocale, tuple[str, str]] = {
    "en": STATIC_COLLEGE_MANDATORY,
    "es": (
        "¿Qué carreras de {school} llevan con más frecuencia a sus graduados a {career}?",
        "¿Cómo puedo complementar esta carrera con las habilidades sugeridas arriba — "
        "mediante cursos, clubes o prácticas que ya ofrecen?",
    ),
    "ar": (
        "ما التخصصات في {school} التي تقود خريجيها في الغالب إلى {career}؟",
        "كيف يمكنني تعزيز هذا التخصص بالمهارات المقترحة أعلاه — من خلال "
        "المواد الدراسية أو النوادي أو التدريب الذي توفّرونه حالياً؟",
    ),
}

_STATIC_COLLEGE_FALLBACK_BY_LOCALE: dict[AppLocale, str] = {
    "en": STATIC_COLLEGE_FALLBACK,
    "es": (
        "¿Qué datos de resultados publican para este programa — ingresos medianos "
        "un año después de graduarse, tasa de empleo, deuda promedio al graduarse?"
    ),
    "ar": (
        "ما بيانات النتائج التي تنشرونها لهذا البرنامج — متوسط الدخل بعد سنة "
        "من التخرج، ومعدّل التوظيف، ومتوسط الديون عند التخرج؟"
    ),
}

_STATIC_COLLEGE_MISSING_EARNINGS_BY_LOCALE: dict[AppLocale, str] = {
    "en": STATIC_COLLEGE_MISSING_EARNINGS,
    "es": (
        "No se publican datos federales de ingresos para su programa de "
        "{program}. ¿Cuántos estudiantes se gradúan cada año y qué porcentaje "
        "toma préstamos federales? ¿Hacen seguimiento interno de los "
        "resultados tras la graduación?"
    ),
    "ar": (
        "لا تُنشر بيانات الأجور الفيدرالية لبرنامج {program} لديكم. "
        "كم عدد الخريجين سنوياً، وما نسبة من يأخذون قروضاً فيدرالية؟ "
        "وهل تتابعون داخلياً نتائج ما بعد التخرج؟"
    ),
}

_STATIC_PARENTS_FALLBACK_BY_LOCALE: dict[AppLocale, tuple[str, ...]] = {
    "en": STATIC_PARENTS_FALLBACK,
    "es": (
        "Si los números del préstamo en la página 1 son correctos, ¿puede la "
        "persona adulta a cargo cubrir ese pago mensual junto con todo lo demás "
        "después de que me gradúe?",
        "¿Qué carrera viste de cerca al crecer — y qué de ella querrías para mí, "
        "o querrías evitarme?",
    ),
    "ar": (
        "إذا كانت أرقام القرض في الصفحة 1 دقيقة، فهل يستطيع وليّ الأمر تحمّل "
        "هذا القسط الشهري إلى جانب باقي النفقات بعد تخرّجي؟",
        "أي مسيرة مهنية رأيتموها عن قرب أثناء نشأتكم — وما الذي تتمنّوْنه لي منها، "
        "أو ما الذي تتمنّوْن أن أتجنّبه؟",
    ),
}

_STATIC_YOURSELF_FALLBACK_BY_LOCALE: dict[AppLocale, tuple[str, ...]] = {
    "en": STATIC_YOURSELF_FALLBACK,
    "es": (
        "¿Seguiré queriendo hacer este trabajo dentro de 10 años si el día a día "
        "se parece al perfil de tareas de O*NET en la página 1?",
        "¿Estoy eligiendo esta carrera porque me interesa, o porque me resulta "
        "familiar — y sabría notar la diferencia todavía?",
    ),
    "ar": (
        "هل سأظلّ أرغب في القيام بهذا العمل بعد 10 سنوات إذا كان اليوم "
        "اليومي يشبه ملف مهام O*NET في الصفحة 1؟",
        "هل أختار هذا التخصص لأنه يثير اهتمامي، أم لأنه مألوف لي — "
        "وهل أعرف الفرق بعد؟",
    ),
}


_LANGUAGE_DIRECTIVE: dict[AppLocale, str] = {
    "en": "",
    "es": (
        "\n\nIMPORTANT: Write every question in natural Spanish (es). "
        "Keep proper nouns (school name, career title, acronyms like O*NET / BLS) "
        "in their original form — do not translate them."
    ),
    "ar": (
        "\n\nIMPORTANT: Write every question in natural Arabic (ar). "
        "Keep proper nouns (school name, career title, acronyms like O*NET / BLS) "
        "in their original form — do not translate them. "
        "Use Modern Standard Arabic; the audience is a high-school student."
    ),
}


# ---------------------------------------------------------------------------
# Gemma system prompt (§4 Gemma System Prompt and JSON Schema).
# ---------------------------------------------------------------------------

_SYSTEM = (
    "You write follow-up questions for a one-page printed report a high "
    "school student takes home from a 90-second guidance-counselor "
    "conversation. The report shows a school, a major, a likely career, a "
    "five-stat profile, a five-row risk profile, and a cost-and-earnings "
    "strip. The student will read these questions aloud or silently with a "
    "counselor, with a parent, and to themselves.\n\n"
    "Voice: candid, concrete, useful. Coach posture, not cheerleader. "
    "Treat the student and audience as adults making a six-figure decision. "
    "No flattery, no hype, no apology. Each question is one sentence and "
    "names something specific from the build context (a school, a career, "
    "a risk factor, a number) — never a vague 'your future' or 'your "
    "passion'.\n\n"
    "Audience-voice rules (strict):\n"
    "- ask_the_college: audience-first. The student is talking to admissions, "
    "  a department head, or a counselor. Use action verbs ('publish', "
    "  'show', 'connect', 'tour') and refer to the school by name. NEVER "
    "  start with 'Will I' or 'Am I'.\n"
    "- ask_your_parents: audience-first. The student is at the kitchen "
    "table with a parent, guardian, or other family adult — do NOT "
    "assume the audience is a biological parent. Use neutral references "
    "('the family adult', 'you'), use shared verbs ('carry', 'cover', "
    "'spare'). NEVER start with 'Will I' or 'Am I'.\n"
    "- ask_yourself: student-first. The student is asking themselves. "
    "  Start with 'Will I', 'Am I', 'Do I', or 'Would I'. Present-future "
    "  tense. NEVER address an external audience.\n\n"
    "Anchor each question to a concrete element of the build. If the top "
    "risk is debt burden, write a debt question. If the top risk is AI "
    "displacement, write an AI question. Don't write the same question "
    "twice across audiences in different words.\n\n"
    "Outcome direction (strict — past failures here have produced "
    "contradictory questions):\n"
    "- Items listed as CLEARED in the user message are CONFIRMED GOOD "
    "outcomes. Never write a question that implies the student failed "
    "at them. A cleared 'Earnings ceiling' means wages grow strongly "
    "over 15 years — do NOT ask 'will I be satisfied with a low "
    "earnings ceiling?'. A cleared 'Job market outlook' means demand "
    "is healthy — do NOT ask if the student is okay with weak demand.\n"
    "- Items listed as NEEDS ATTENTION are the unresolved risks. These "
    "are the only places it is appropriate to write a coping or "
    "trade-off question.\n"
    "- If you have nothing useful to add for ask_yourself beyond the "
    "needs-attention list, return an empty array. Static fallbacks "
    "fill any gap.\n\n"
    "FORBIDDEN VOCABULARY — these terms appear in the in-app product but "
    "MUST NOT appear in any output you produce here. The output is for a "
    "printed advisory report and these terms read as unserious in print:\n"
    "  boss, boss fight, gauntlet, fight, win, lose, draw, won, lost, "
    "  reroll, build, builds, level up, ERN, ROI, RES, GRW, AURA, "
    "  HMN, Fight AI, Fight Student Loans, Fight the Market, Fight "
    "  Burnout, Fight the Ceiling, Fight the Future, WIN, DRAW, LOSE.\n"
    "If you need to refer to the cost-vs-earnings ratio, say 'debt-to-"
    "earnings' or 'debt service'. If you need to refer to AI exposure, "
    "say 'AI displacement', 'automation', or 'AI exposure'. If you need "
    "to refer to the program, say 'this program' or 'this major', not "
    "'this build' or 'this plan'.\n\n"
    "Length: each question is one sentence, 240 characters maximum.\n"
    "Count: zero to three questions per audience. Write fewer if you have "
    "nothing useful to add — the report has guaranteed static questions "
    "filling any gaps. Do not pad. Do not write filler.\n\n"
    "Output format: valid JSON, exactly this schema, no prose, no "
    "code-fence, no commentary. Each array holds zero to three short "
    "question strings. Example shape (illustrative only — do not echo "
    "these exact strings):\n"
    '{"ask_the_college": ["Question for the college?"], '
    '"ask_your_parents": ["Question for the family adult?"], '
    '"ask_yourself": ["Will I question for myself?"]}\n'
    "If you cannot write a question for an audience, return an empty "
    "array for that audience. Do not write 'N/A', do not apologize, do "
    "not explain."
)


# ---------------------------------------------------------------------------
# Build-context scoping (per feedback_scoped_llm_contexts.md).
# ---------------------------------------------------------------------------


def _top_two_risks(build: Build) -> list[tuple[str, str]]:
    """Up-to-2 boss outcomes with the most concerning risk levels.

    Each tuple is (advisory_label, risk_level). ``Insufficient`` rows
    are skipped — Gemma should not be asked to riff on missing data.
    """
    severity = {"High": 0, "Elevated": 1, "Moderate": 2, "Low": 3, "Insufficient": 4}
    rows: list[tuple[str, str, int]] = []
    for boss in BOSS_ORDER:
        # Find this boss's fight in the gauntlet.
        fight = next((f for f in build.gauntlet.fights if f.boss == boss), None)
        if fight is None:
            continue
        level = risk_level_for_boss(boss, fight.raw_score)
        if level == "Insufficient":
            continue
        rows.append((boss_advisory_label(boss), level, severity[level]))
    rows.sort(key=lambda r: r[2])
    return [(label, level) for label, level, _ in rows[:2]]


def _top_two_strengths(build: Build) -> list[tuple[str, str]]:
    """Symmetric to _top_two_risks. Lowest risk = strongest factor."""
    severity = {"Low": 0, "Moderate": 1, "Elevated": 2, "High": 3, "Insufficient": 4}
    rows: list[tuple[str, str, int]] = []
    for boss in BOSS_ORDER:
        fight = next((f for f in build.gauntlet.fights if f.boss == boss), None)
        if fight is None:
            continue
        level = risk_level_for_boss(boss, fight.raw_score)
        if level == "Insufficient":
            continue
        rows.append((boss_advisory_label(boss), level, severity[level]))
    rows.sort(key=lambda r: r[2])
    return [(label, level) for label, level, _ in rows[:2]]


def _user_prompt(build: Build) -> str:
    """Build the small, scoped user message Gemma sees for this PDF.

    Per feedback_scoped_llm_contexts.md, only fields Gemma needs:
    school, major, career, top-2 risks, top-2 strengths. No PII, no raw
    scores, no internal IDs.

    Risk-level vocabulary ("Low"/"High") is intentionally NOT exposed
    alongside the boss labels here because some boss labels are
    direction-flipped from their risk levels — e.g., "Earnings ceiling"
    and "Job market outlook" are positive-direction nouns where "Low
    risk" means a GOOD outcome. Pasting "Earnings ceiling: Low" caused
    Gemma to produce contradictory questions like "Will I be satisfied
    with a low earnings ceiling?" when the student actually cleared the
    fight. Strengths render as ``cleared`` and risks render as
    ``needs attention`` so no label can be parsed as a noun-modifier.
    """
    risks = _top_two_risks(build)
    strengths = _top_two_strengths(build)
    risks_str = (
        "; ".join(f"{lbl} — needs attention" for lbl, _ in risks)
        or "(none ranked)"
    )
    strengths_str = (
        "; ".join(f"{lbl} — cleared" for lbl, _ in strengths) or "(none ranked)"
    )
    major = build.career.program_name or build.major_text or "this program"
    return (
        f"School: {build.school_name}\n"
        f"Major: {major}\n"
        f"Career: {build.career.occupation_title}\n"
        f"Risk factors that NEED ATTENTION: {risks_str}\n"
        f"Outcomes the student CLEARED (do not describe these as "
        f"problems): {strengths_str}\n"
        "\n"
        "Write the JSON object now."
    )


# ---------------------------------------------------------------------------
# Static-fallback assembly.
# ---------------------------------------------------------------------------


def _fit_program_to_template(template: str, program: str) -> str:
    """Truncate ``program`` so ``template.format(program=...)`` fits the
    240-char ``AudienceQuestion.text`` cap across every locale.

    The Spanish missing-earnings template eats ~214 chars of the budget
    before substitution, so a 50-char CIP name like
    "Business Administration, Management and Operations" would crash
    Pydantic validation. This helper measures the actual template at
    runtime so it stays correct across all 3 locales without per-locale
    hardcoded budgets.
    """
    placeholder = "{program}"
    template_overhead = len(template) - len(placeholder)
    budget = 240 - template_overhead - 1  # -1 for safety margin
    if budget < 5:
        # Template alone is already too long — caller should be rewritten.
        return program[:4] + "…"
    if len(program) <= budget:
        return program
    return program[: budget - 1].rstrip() + "…"


def _static_college_questions(
    build: Build, locale: AppLocale = "en",
) -> list[AudienceQuestion]:
    """The 2 mandatory + 1 fallback static college questions (§3.11.4).

    When the build's program-level earnings are suppressed (both ERN and ROI
    are null on the career), a 3rd mandatory question is inserted pointing
    the student at the missing data. Mirrors the InsufficientDataBanner the
    student sees on the build screen.
    """
    school = build.school_name
    career = build.career.occupation_title
    program = build.program_name or build.career.program_name or career
    mandatory = _STATIC_COLLEGE_MANDATORY_BY_LOCALE[locale]
    fallback = _STATIC_COLLEGE_FALLBACK_BY_LOCALE[locale]
    questions: list[AudienceQuestion] = [
        AudienceQuestion(
            text=mandatory[0].format(school=school, career=career),
            is_static_mandatory=True,
        ),
        AudienceQuestion(
            text=mandatory[1],
            is_static_mandatory=True,
        ),
    ]
    if build.career.stats.ern is None and build.career.stats.roi is None:
        missing_template = _STATIC_COLLEGE_MISSING_EARNINGS_BY_LOCALE[locale]
        fitted_program = _fit_program_to_template(missing_template, program)
        questions.append(
            AudienceQuestion(
                text=missing_template.format(program=fitted_program),
                is_static_mandatory=True,
            )
        )
    questions.append(AudienceQuestion(text=fallback))
    return questions


def _static_parents_questions(locale: AppLocale = "en") -> list[AudienceQuestion]:
    return [
        AudienceQuestion(text=q)
        for q in _STATIC_PARENTS_FALLBACK_BY_LOCALE[locale]
    ]


def _static_yourself_questions(locale: AppLocale = "en") -> list[AudienceQuestion]:
    return [
        AudienceQuestion(text=q)
        for q in _STATIC_YOURSELF_FALLBACK_BY_LOCALE[locale]
    ]


def _all_static(build: Build, locale: AppLocale = "en") -> tuple[
    list[AudienceQuestion],
    list[AudienceQuestion],
    list[AudienceQuestion],
]:
    return (
        _static_college_questions(build, locale),
        _static_parents_questions(locale),
        _static_yourself_questions(locale),
    )


# ---------------------------------------------------------------------------
# Response parsing + validation.
# ---------------------------------------------------------------------------


_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.S)


def _strip_code_fence(raw: str) -> str:
    """Strip optional ``` / ```json fencing — A3 from genai-architect §10."""
    return _CODE_FENCE_RE.sub("", raw).strip()


def _has_forbidden_term(text: str) -> bool:
    """True if ``text`` contains any term from FORBIDDEN_IN_GEMMA_OUTPUT."""
    return contains_forbidden_term(text, FORBIDDEN_IN_GEMMA_OUTPUT)


def _parse_response(raw: str) -> dict[str, list[str]] | None:
    """Parse a Gemma response into the 3-audience dict, or None on failure.

    None signals a "fallback_malformed" path. Caller distinguishes
    empty-response (raw == "") from malformed (raw != "" but unparseable).
    """
    if not raw:
        return None
    stripped = _strip_code_fence(raw)
    try:
        obj = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(obj, dict):
        return None
    out: dict[str, list[str]] = {}
    for key in ("ask_the_college", "ask_your_parents", "ask_yourself"):
        v = obj.get(key)
        if not isinstance(v, list):
            return None
        clean: list[str] = []
        for item in v:
            if not isinstance(item, str):
                return None
            text = item.strip()
            if not text:
                continue
            if len(text) > 240:
                # Spec contract — anything > 240 chars is malformed output.
                return None
            if _has_forbidden_term(text):
                return None
            clean.append(text)
        out[key] = clean
    return out


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------


def _assemble(
    college: list[AudienceQuestion],
    parents: list[AudienceQuestion],
    yourself: list[AudienceQuestion],
    *,
    gemma_path: GemmaPath,
) -> AudienceQuestions:
    """Cap each audience at 5 (Pydantic max) and floor at 1."""
    return AudienceQuestions(
        ask_the_college=college[:5],
        ask_your_parents=parents[:5],
        ask_yourself=yourself[:5],
        gemma_path=gemma_path,
    )


def _live_assemble(
    build: Build,
    parsed: dict[str, list[str]],
    locale: AppLocale = "en",
) -> AudienceQuestions:
    """Successful Gemma path: 2 mandatory college Qs + Gemma's additions.

    Static fallbacks fill the floor of 1 for parents/yourself when Gemma
    returns an empty array for that audience.
    """
    # Preserve every mandatory entry — there are 2 by default and 3 when
    # the build's earnings stats are suppressed (the new missing-earnings
    # question). Drop only the non-mandatory fallback so Gemma can fill
    # the remaining slots. The college audience caps at 5 in _assemble.
    all_static = _static_college_questions(build, locale)
    mandatory = [q for q in all_static if q.is_static_mandatory]
    gemma_slots = max(0, 5 - len(mandatory))
    college = mandatory + [
        AudienceQuestion(text=t)
        for t in parsed["ask_the_college"][:gemma_slots]
    ]

    parents_live = parsed["ask_your_parents"]
    if parents_live:
        parents = [AudienceQuestion(text=t) for t in parents_live]
    else:
        parents = _static_parents_questions(locale)

    yourself_live = parsed["ask_yourself"]
    if yourself_live:
        yourself = [AudienceQuestion(text=t) for t in yourself_live]
    else:
        yourself = _static_yourself_questions(locale)

    return _assemble(college, parents, yourself, gemma_path="live")


def _fallback(
    build: Build, path: GemmaPath, locale: AppLocale = "en",
) -> AudienceQuestions:
    """Static-only assembly — guaranteed non-empty per spec contract."""
    college, parents, yourself = _all_static(build, locale)
    return _assemble(college, parents, yourself, gemma_path=path)


async def generate_audience_questions(
    build: Build,
    *,
    timeout_s: float = 6.0,
    locale: AppLocale | None = None,
) -> AudienceQuestions:
    """Generate the 3-audience question set via a single scoped Gemma call.

    Always returns a non-empty AudienceQuestions. Every code path emits
    exactly one ``logs/gemma.jsonl`` record. See module docstring + spec
    §4 ``pdf_questions.py`` for the full contract.

    ``locale`` controls both the Gemma "respond in this language" directive
    and the static fallback strings used when Gemma is unavailable. When
    omitted, falls back to the build's own locale so a re-export under a
    different language is opt-in.
    """
    loc: AppLocale = normalize_locale(locale if locale is not None else build.locale)
    extra = {"call_site": "pdf_questions"}
    user_msg = _user_prompt(build)
    system_prompt = _SYSTEM + _LANGUAGE_DIRECTIVE.get(loc, "")

    try:
        raw = await asyncio.wait_for(
            gemma_client.generate_chat_async(
                system=system_prompt,
                messages=[{"role": "user", "content": user_msg}],
                max_tokens=400,
                temperature=0.3,
                extra=extra,
                timeout_s=timeout_s,
                response_format="json",
            ),
            timeout=timeout_s + 1.0,
        )
    except asyncio.TimeoutError:
        gemma_client.log_synthetic_event(
            call_site="pdf_questions",
            event="fallback_timeout",
            extra={"reason": "asyncio.TimeoutError"},
        )
        return _fallback(build, "fallback_timeout", loc)
    except Exception as exc:
        # The gemma_client itself catches and returns "" on transport
        # error — but if this path raises (e.g. cold env, missing config)
        # we treat it as a disabled-backend signal.
        gemma_client.log_synthetic_event(
            call_site="pdf_questions",
            event="fallback_disabled",
            extra={"reason": f"{type(exc).__name__}: {exc}"},
        )
        logger.warning("pdf_questions: gemma client unavailable: %s", exc)
        return _fallback(build, "fallback_disabled", loc)

    if not raw:
        gemma_client.log_synthetic_event(
            call_site="pdf_questions",
            event="fallback_empty",
        )
        return _fallback(build, "fallback_empty", loc)

    parsed = _parse_response(raw)
    if parsed is None:
        gemma_client.log_synthetic_event(
            call_site="pdf_questions",
            event="fallback_malformed",
            extra={"raw_preview": raw[:300]},
        )
        return _fallback(build, "fallback_malformed", loc)

    return _live_assemble(build, parsed, loc)
