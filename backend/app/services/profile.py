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

_active_profiles: set[str] = set()
_profiles_lock = threading.Lock()

_MAX_RETRIES = 10


def _normalize(name: str) -> str:
    return " ".join(name.lower().split())


def _strip_emoji(name: str) -> str:
    return re.sub(r"[^\w\s]", "", name, flags=re.UNICODE).strip()


def generate_name(exclude: set[str] | None = None) -> ProfileResult:
    excluded = exclude or set()
    with _profiles_lock:
        for _ in range(_MAX_RETRIES):
            adj1 = random.choice(ADJECTIVES_1)
            adj2 = random.choice(ADJECTIVES_2)
            animal_name, animal_emoji = random.choice(ANIMALS)
            display = f"{adj1} {adj2} {animal_name}".title()
            normalized = _normalize(display)
            if normalized not in _active_profiles and normalized not in excluded:
                _active_profiles.add(normalized)
                return ProfileResult(
                    profile_name=display,
                    animal_emoji=animal_emoji,
                    animal_name=animal_name,
                )

        adj1 = random.choice(ADJECTIVES_1)
        adj2 = random.choice(ADJECTIVES_2) + str(random.randint(1, 9))
        animal_name, animal_emoji = random.choice(ANIMALS)
        display = f"{adj1} {adj2} {animal_name}".title()
        _active_profiles.add(_normalize(display))
        return ProfileResult(
            profile_name=display,
            animal_emoji=animal_emoji,
            animal_name=animal_name,
        )


def reroll(current_name: str) -> ProfileResult:
    return generate_name(exclude={_normalize(current_name)})


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
