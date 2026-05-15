"""Three-word profile name generation, collision detection, fuzzy lookup.

Students get a whimsical name (adjective + adjective + animal emoji)
as their identity. No PII, no accounts, no passwords.
"""

from __future__ import annotations

import logging
import random
import re
import threading
from difflib import get_close_matches

from app.models.career import BuildSummary, ProfileLookupResult, ProfileResult
from app.services import builds as builds_service
from app.services.locale import AppLocale, normalize_locale

logger = logging.getLogger(__name__)

ADJECTIVES_1 = [
    "brave", "bold", "bright", "calm", "clever",
    "cosmic", "cozy", "daring", "dancing", "dreamy",
    "eager", "electric", "epic", "fearless", "fierce",
    "free", "gentle", "glad", "glowing", "golden",
    "grand", "happy", "humble", "keen", "kind",
    "lively", "lucky", "loyal", "magic", "merry",
    "mighty", "noble", "plucky", "proud", "quick",
    "quiet", "rad", "ready", "rising", "roaming",
    "shining", "smooth", "snappy", "soaring", "sparky",
    "speedy", "spirited", "steady", "stellar", "stoked",
]

ADJECTIVES_2 = [
    "agile", "awesome", "breezy", "chill", "clear",
    "crisp", "curious", "dapper", "deft", "earnest",
    "fair", "fancy", "fleet", "fluffy", "focused",
    "fresh", "frisky", "fun", "fuzzy", "groovy",
    "gutsy", "handy", "hearty", "honest", "jazzy",
    "joyful", "jumpy", "legit", "nimble", "nifty",
    "peppy", "perky", "plush", "polished", "prime",
    "pumped", "quirky", "rare", "real", "robust",
    "savvy", "sharp", "slick", "snug", "solid",
    "spry", "sure", "swift", "true", "vivid",
]

ANIMALS = [
    ("bear", "\U0001f43b"),
    ("bunny", "\U0001f430"),
    ("turtle", "\U0001f422"),
    ("chipmunk", "\U0001f43f\ufe0f"),
    ("fox", "\U0001f98a"),
    ("owl", "\U0001f989"),
    ("penguin", "\U0001f427"),
    ("cat", "\U0001f431"),
]

# Locale-keyed vocabularies. English keeps the canonical 50/50/8 lists
# above as the default. Spanish + Arabic ship smaller (\u224825/25/8) lists
# tuned for the same "whimsical three-word" voice. _MAX_RETRIES (10)
# is plenty of collision headroom \u2014 25*25*8 = 5000 distinct names per
# non-en locale before we even fall back to the digit-suffix path.
# Animal emojis are shared across locales \u2014 the only thing that
# changes per locale is the animal NAME used in the printed string.
_ADJECTIVES_1_BY_LOCALE: dict[AppLocale, list[str]] = {
    "en": ADJECTIVES_1,
    "es": [
        "valiente", "audaz", "brillante", "tranquilo", "astuto",
        "c\u00f3smico", "alegre", "atrevido", "so\u00f1ador", "ansioso",
        "el\u00e9ctrico", "\u00e9pico", "fiero", "libre", "gentil",
        "dorado", "feliz", "humilde", "amable", "vivaz",
        "afortunado", "leal", "m\u00e1gico", "alegre", "fuerte",
    ],
    "ar": [
        "\u0634\u062c\u0627\u0639", "\u062c\u0631\u064a\u0621", "\u0644\u0627\u0645\u0639", "\u0647\u0627\u062f\u0626", "\u0630\u0643\u064a",
        "\u0643\u0648\u0646\u064a", "\u0645\u0631\u064a\u062d", "\u0645\u063a\u0627\u0645\u0631", "\u062d\u0627\u0644\u0645", "\u0645\u062a\u062d\u0645\u0633",
        "\u0643\u0647\u0631\u0628\u0627\u0626\u064a", "\u0645\u0644\u062d\u0645\u064a", "\u0634\u0631\u0633", "\u062d\u0631", "\u0644\u0637\u064a\u0641",
        "\u0630\u0647\u0628\u064a", "\u0633\u0639\u064a\u062f", "\u0645\u062a\u0648\u0627\u0636\u0639", "\u062d\u0627\u0632\u0645", "\u0646\u0634\u064a\u0637",
        "\u0645\u062d\u0638\u0648\u0638", "\u0648\u0641\u064a", "\u0633\u0627\u062d\u0631", "\u0628\u0647\u064a\u062c", "\u0642\u0648\u064a",
    ],
}

_ADJECTIVES_2_BY_LOCALE: dict[AppLocale, list[str]] = {
    "en": ADJECTIVES_2,
    "es": [
        "\u00e1gil", "asombroso", "fresco", "sereno", "claro",
        "curioso", "elegante", "diestro", "sincero", "justo",
        "veloz", "esponjoso", "enfocado", "nuevo", "juguet\u00f3n",
        "divertido", "valiente", "amable", "honesto", "vivaz",
        "ingenioso", "\u00e1gil", "n\u00edtido", "pulcro", "aut\u00e9ntico",
    ],
    "ar": [
        "\u0631\u0634\u064a\u0642", "\u0631\u0627\u0626\u0639", "\u0645\u0646\u0639\u0634", "\u0635\u0627\u0641\u064d", "\u0648\u0627\u0636\u062d",
        "\u0641\u0636\u0648\u0644\u064a", "\u0623\u0646\u064a\u0642", "\u0628\u0627\u0631\u0639", "\u0635\u0627\u062f\u0642", "\u0639\u0627\u062f\u0644",
        "\u0633\u0631\u064a\u0639", "\u0643\u062b\u064a\u0641", "\u0645\u0631\u0643\u0651\u0632", "\u062c\u062f\u064a\u062f", "\u0645\u0631\u062d",
        "\u0645\u0645\u062a\u0639", "\u0634\u062c\u0627\u0639", "\u0648\u062f\u0648\u062f", "\u0623\u0645\u064a\u0646", "\u062d\u064a\u0648\u064a",
        "\u0630\u0643\u064a", "\u0646\u0628\u064a\u0644", "\u062d\u0627\u062f", "\u0623\u0635\u064a\u0644", "\u062d\u0642\u064a\u0642\u064a",
    ],
}

# Animal names per locale. The 8 emojis are shared (Unicode glyphs are
# universal); only the localized noun changes. Use Modern Standard
# Arabic for the ar names.
_ANIMALS_BY_LOCALE: dict[AppLocale, list[tuple[str, str]]] = {
    "en": ANIMALS,
    "es": [
        ("oso", "\U0001f43b"),
        ("conejo", "\U0001f430"),
        ("tortuga", "\U0001f422"),
        ("ardilla", "\U0001f43f\ufe0f"),
        ("zorro", "\U0001f98a"),
        ("b\u00faho", "\U0001f989"),
        ("ping\u00fcino", "\U0001f427"),
        ("gato", "\U0001f431"),
    ],
    "ar": [
        ("\u062f\u0628", "\U0001f43b"),
        ("\u0623\u0631\u0646\u0628", "\U0001f430"),
        ("\u0633\u0644\u062d\u0641\u0627\u0629", "\U0001f422"),
        ("\u0633\u0646\u062c\u0627\u0628", "\U0001f43f\ufe0f"),
        ("\u062b\u0639\u0644\u0628", "\U0001f98a"),
        ("\u0628\u0648\u0645\u0629", "\U0001f989"),
        ("\u0628\u0637\u0631\u064a\u0642", "\U0001f427"),
        ("\u0642\u0637", "\U0001f431"),
    ],
}

_active_profiles: set[str] = set()
_profiles_lock = threading.Lock()

_MAX_RETRIES = 10


def _normalize(name: str) -> str:
    return " ".join(name.lower().split())


def _strip_emoji(name: str) -> str:
    return re.sub(r"[^\w\s]", "", name, flags=re.UNICODE).strip()


def _format_display(adj1: str, adj2: str, animal_name: str, locale: AppLocale) -> str:
    """Title-case English output; leave non-Latin scripts alone.

    Python's ``str.title()`` is destructive on Arabic (no concept of case)
    and Spanish (uppercases accented vowels in a way the canonical
    Spanish style guide doesn't always want for noun phrases like
    "Valiente brillante zorro"). For Spanish we capitalize the first
    word only; for Arabic we leave the phrase as-is.
    """
    joined = f"{adj1} {adj2} {animal_name}"
    if locale == "en":
        return joined.title()
    if locale == "es":
        # Capitalize the first letter; preserve the rest of the casing.
        return joined[:1].upper() + joined[1:]
    return joined


def generate_name(
    exclude: set[str] | None = None,
    locale: AppLocale | None = None,
) -> ProfileResult:
    excluded = exclude or set()
    loc: AppLocale = normalize_locale(locale)
    adj1_pool = _ADJECTIVES_1_BY_LOCALE.get(loc, ADJECTIVES_1)
    adj2_pool = _ADJECTIVES_2_BY_LOCALE.get(loc, ADJECTIVES_2)
    animal_pool = _ANIMALS_BY_LOCALE.get(loc, ANIMALS)
    with _profiles_lock:
        for _ in range(_MAX_RETRIES):
            adj1 = random.choice(adj1_pool)
            adj2 = random.choice(adj2_pool)
            animal_name, animal_emoji = random.choice(animal_pool)
            display = _format_display(adj1, adj2, animal_name, loc)
            normalized = _normalize(display)
            if normalized not in _active_profiles and normalized not in excluded:
                _active_profiles.add(normalized)
                return ProfileResult(
                    profile_name=display,
                    animal_emoji=animal_emoji,
                    animal_name=animal_name,
                )

        # Retry budget exhausted — fall through to a digit-suffixed name
        # to guarantee uniqueness. Cheap enough that the user never
        # notices; happens roughly 1-in-a-million for these vocabularies.
        adj1 = random.choice(adj1_pool)
        adj2 = random.choice(adj2_pool) + str(random.randint(1, 9))
        animal_name, animal_emoji = random.choice(animal_pool)
        display = _format_display(adj1, adj2, animal_name, loc)
        _active_profiles.add(_normalize(display))
        return ProfileResult(
            profile_name=display,
            animal_emoji=animal_emoji,
            animal_name=animal_name,
        )


def reroll(
    current_name: str, locale: AppLocale | None = None,
) -> ProfileResult:
    return generate_name(exclude={_normalize(current_name)}, locale=locale)


def lookup(name_query: str) -> ProfileLookupResult:
    normalized = _normalize(name_query)

    if normalized in _active_profiles:
        emoji = _find_emoji(normalized)
        animal = _find_animal_name(normalized)
        return ProfileLookupResult(
            found=True,
            profile_name=normalized,
            animal_emoji=emoji,
            animal_name=animal,
            builds=_get_builds_for_profile(normalized),
        )

    text_only = _strip_emoji(normalized)
    all_names = list(_active_profiles)
    all_text = [_strip_emoji(n) for n in all_names]

    matches = get_close_matches(text_only, all_text, n=1, cutoff=0.6)
    if matches:
        idx = all_text.index(matches[0])
        matched_name = all_names[idx]
        from difflib import SequenceMatcher
        ratio = SequenceMatcher(None, text_only, matches[0]).ratio()
        if ratio >= 0.8:
            emoji = _find_emoji(matched_name)
            animal = _find_animal_name(matched_name)
            return ProfileLookupResult(
                found=True,
                profile_name=matched_name,
                animal_emoji=emoji,
                animal_name=animal,
                builds=_get_builds_for_profile(matched_name),
            )
        return ProfileLookupResult(
            found=False,
            suggestion=matched_name,
        )

    return ProfileLookupResult(found=False)


def register_profile(profile_name: str) -> None:
    _active_profiles.add(_normalize(profile_name))


def _load_existing_profiles() -> None:
    """Seed the in-memory profile set from persisted builds.

    Queries the DuckDB ``builds`` table for distinct profile_name values
    rather than globbing JSON files. Safe to call on startup even when
    the DB doesn't exist yet — the builds service creates the schema
    on first connection.
    """
    try:
        rows = builds_service._conn().execute(
            "SELECT DISTINCT profile_name FROM builds WHERE profile_name != ''"
        ).fetchall()
    except Exception as exc:
        logger.debug("Could not load existing profiles: %s", exc)
        return
    for (name,) in rows:
        if name:
            _active_profiles.add(_normalize(name))


def _find_emoji(normalized_name: str) -> str:
    for animal_name, emoji in ANIMALS:
        if animal_name in normalized_name:
            return emoji
    return ""


def _find_animal_name(normalized_name: str) -> str:
    for animal_name, _emoji in ANIMALS:
        if animal_name in normalized_name:
            return animal_name
    return ""


def _get_builds_for_profile(normalized_name: str) -> list[BuildSummary]:
    """Return all builds for a normalized profile name.

    Profile names are stored on the Build in their original (display)
    form. We normalize both sides before comparing so a lookup for
    "Steady Bold Turtle 🐢" matches a build saved with the emoji in
    the name.
    """
    try:
        summaries = builds_service.list_builds()
    except Exception as exc:
        logger.debug("Could not list builds for profile %r: %s", normalized_name, exc)
        return []
    return [
        summary for summary in summaries
        if _normalize(summary.profile_name) == normalized_name
    ]
