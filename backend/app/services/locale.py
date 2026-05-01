"""Locale helpers — normalizer + Gemma language instructions.

Supports ``en`` (English), ``es`` (Spanish), and ``ar`` (Arabic). The
``gemma_language_instruction`` function returns a block that can be
appended to any Gemma system prompt to constrain output language while
preserving canonical data values.
"""

from __future__ import annotations

from typing import Literal

AppLocale = Literal["en", "es", "ar"]
DEFAULT_LOCALE: AppLocale = "en"


def normalize_locale(value: object) -> AppLocale:
    if value == "es":
        return "es"
    if value == "ar":
        return "ar"
    return "en"


_EN_INSTRUCTION = (
    "Write student-facing prose in English.\n"
    "Preserve official school names, occupation titles, source names and "
    "their acronyms (BLS, O*NET, IPEDS, BEA, College Scorecard), program "
    "names, dollar amounts, percentages, codes, and JSON keys exactly."
)

_ES_INSTRUCTION = (
    "Write all student-facing prose in Spanish.\n"
    "Use the glossary below for product concepts when they appear.\n"
    "Preserve official school names, occupation titles, source names and "
    "their acronyms (BLS, O*NET, IPEDS, BEA, College Scorecard), program "
    "names, dollar amounts, percentages, codes, and JSON keys exactly.\n"
    "You may explain what an official English title means in Spanish after "
    "naming it, but do not replace the canonical title.\n"
    "After the first reference to a data source, use only its English "
    "acronym (BLS, O*NET, IPEDS, BEA). Do not translate these acronyms.\n\n"
    "If your response includes a JSON section or structured output, keep "
    "all JSON keys and enum values in English exactly as specified — "
    'including values like "high", "medium", "low", "COMMON", '
    '"LESS_COMMON", "STRETCH", and all CIP/SOC codes. Only translate '
    "free-text prose fields (such as "
    '"reasoning", "rationale", "message", "narrowing_hint", "why").\n\n'
    "Glossary:\n"
    "- student debt = deuda estudiantil\n"
    "- career paths = trayectorias profesionales\n"
    "- job outlook = perspectiva laboral\n"
    "- AI exposure = exposición a la IA\n"
    "- human edge = ventaja humana\n"
    "- data is estimated = los datos son estimados\n"
    "- salary = salario\n"
    "- median salary = salario medio\n"
    "- student loan = préstamo estudiantil\n"
    "- guidance counselor = consejero escolar\n"
    "- debt-to-income = deuda en relación con los ingresos\n"
    "- next steps = próximos pasos\n"
    "- cost of attendance = costo de asistencia\n"
    "- purchasing power = poder adquisitivo"
)


_AR_INSTRUCTION = (
    "Write all student-facing prose in Modern Standard Arabic (الفصحى).\n"
    "Use the glossary below for product concepts when they appear.\n"
    "Preserve official school names, occupation titles, source names and "
    "their acronyms (BLS, O*NET, IPEDS, BEA, College Scorecard), program "
    "names, dollar amounts, percentages, codes, and JSON keys exactly — "
    "render them as-is in the original Latin script, do not transliterate "
    "into Arabic letters.\n"
    "You may explain what an official English title means in Arabic after "
    "naming it, but do not replace the canonical title.\n"
    "After the first reference to a data source, use only its English "
    "acronym (BLS, O*NET, IPEDS, BEA). Do not translate these acronyms.\n"
    "Use Western Arabic numerals (0-9), not Eastern Arabic numerals "
    "(٠-٩), for all dollar amounts, percentages, years, and codes — "
    "this matches the rest of the app and the underlying data.\n\n"
    "If your response includes a JSON section or structured output, keep "
    "all JSON keys and enum values in English exactly as specified — "
    'including values like "high", "medium", "low", "COMMON", '
    '"LESS_COMMON", "STRETCH", and all CIP/SOC codes. Only translate '
    "free-text prose fields (such as "
    '"reasoning", "rationale", "message", "narrowing_hint", "why").\n\n'
    "Glossary:\n"
    "- student debt = الديون الطلابية\n"
    "- career paths = المسارات المهنية\n"
    "- job outlook = آفاق التوظيف\n"
    "- AI exposure = التعرض للذكاء الاصطناعي\n"
    "- human edge = الميزة الإنسانية\n"
    "- data is estimated = البيانات تقديرية\n"
    "- salary = الراتب\n"
    "- median salary = الراتب الوسيط\n"
    "- student loan = القرض الطلابي\n"
    "- guidance counselor = المرشد الأكاديمي\n"
    "- debt-to-income = نسبة الدين إلى الدخل\n"
    "- next steps = الخطوات التالية\n"
    "- cost of attendance = تكلفة الدراسة\n"
    "- purchasing power = القوة الشرائية"
)


def gemma_language_instruction(locale: AppLocale) -> str:
    locale = normalize_locale(locale)
    if locale == "es":
        return _ES_INSTRUCTION
    if locale == "ar":
        return _AR_INSTRUCTION
    return _EN_INSTRUCTION


# ---------------------------------------------------------------------------
# Fallback copy — shown when Gemma is unreachable.
# ---------------------------------------------------------------------------

_FALLBACKS: dict[str, dict[AppLocale, str]] = {
    "gemma_unreachable": {
        "en": (
            "Gemma is unavailable right now. "
            "Your data is still loaded — try again in a moment."
        ),
        "es": (
            "Gemma no está disponible en este momento. "
            "Tus datos siguen cargados — inténtalo de nuevo."
        ),
        "ar": (
            "Gemma غير متاح في الوقت الحالي. "
            "بياناتك لا تزال محمّلة — حاول مرة أخرى بعد قليل."
        ),
    },
    "guidance_unavailable": {
        "en": (
            "The full write-up didn't load this time "
            "— you can come back to it."
        ),
        "es": (
            "El análisis completo no se cargó esta vez "
            "— puedes volver a intentarlo."
        ),
        "ar": (
            "لم يتم تحميل التحليل الكامل هذه المرة "
            "— يمكنك العودة إليه لاحقاً."
        ),
    },
    "next_steps_unavailable": {
        "en": (
            "Your action plan didn't load this time "
            "— try again in a moment."
        ),
        "es": (
            "Tu plan de acción no se cargó esta vez "
            "— inténtalo de nuevo en un momento."
        ),
        "ar": (
            "لم يتم تحميل خطة العمل هذه المرة "
            "— حاول مرة أخرى بعد قليل."
        ),
    },
    "boss_unknown_ai": {
        "en": (
            "There isn't enough data to say "
            "how AI will affect this career."
        ),
        "es": (
            "No hay suficientes datos para decir "
            "cómo la IA afectará esta carrera."
        ),
        "ar": (
            "لا تتوفر بيانات كافية لتحديد "
            "كيف سيؤثر الذكاء الاصطناعي على هذه المهنة."
        ),
    },
    "boss_unknown_loans": {
        "en": (
            "There isn't enough data to compare "
            "the debt to the starting salary."
        ),
        "es": (
            "No hay suficientes datos para comparar "
            "la deuda con el salario inicial."
        ),
        "ar": (
            "لا تتوفر بيانات كافية لمقارنة "
            "الديون بالراتب الابتدائي."
        ),
    },
    "chat_unavailable": {
        "en": (
            "I'm having trouble reaching Gemma right now. "
            "Try the question again in a moment."
        ),
        "es": (
            "Tengo problemas para conectar con Gemma ahora. "
            "Intenta la pregunta de nuevo en un momento."
        ),
        "ar": (
            "أواجه صعوبة في الاتصال بـ Gemma الآن. "
            "حاول طرح السؤال مرة أخرى بعد قليل."
        ),
    },
}


def fallback_text(key: str, locale: AppLocale) -> str:
    locale = normalize_locale(locale)
    entry = _FALLBACKS.get(key, {})
    return entry.get(locale) or entry.get("en", "")
