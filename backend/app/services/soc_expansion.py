"""Gemma-driven SOC universe expansion.

When a student's stated intent demands SOCs the BLS CIP-SOC crosswalk
doesn't return (e.g. physicians for Biology + pre-med), this module
pre-filters a candidate pool from consumable.occupation_profiles, calls
Gemma with a tools=[expand_socs] schema, and returns the union of
crosswalk SOCs plus Gemma's intent-driven picks (capped at 5).

When neither trigger fires: pure pass-through, no Gemma call.
When Gemma fails or returns nothing parseable: returns base_socs.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable

from app.services import gemma_client

logger = logging.getLogger(__name__)

EXPANSION_CAP: int = 5
CANDIDATE_POOL_CAP: int = 30

_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "in", "is", "it", "its", "of", "on", "or", "that", "the",
    "to", "was", "were", "with",
})
_CIP_ADMIN_TERMS = frozenset({
    "general", "other", "specific", "subject", "areas", "programs",
    "studies", "all", "not", "elsewhere", "classified", "nec",
    "miscellaneous",
})

SYNONYM_MAP: dict[str, list[str]] = {
    "doctor": ["physician", "surgeon", "medical"],
    "pre-med": ["physician", "surgeon", "medical"],
    "premed": ["physician", "surgeon", "medical"],
    "pre med": ["physician", "surgeon", "medical"],
    "medicine": ["physician", "surgeon", "medical"],
    "lawyer": ["attorney", "lawyer", "legal", "judicial"],
    "pre-law": ["attorney", "lawyer", "legal", "judicial"],
    "prelaw": ["attorney", "lawyer", "legal", "judicial"],
    "dentist": ["dentist", "dental", "orthodont"],
    "pre-vet": ["veterinar"],
    "vet": ["veterinar"],
    "veterinary": ["veterinar"],
    "nurse": ["nurse", "nursing", "registered nurse"],
    "teacher": ["teacher", "education", "instruction"],
    "teaching": ["teacher", "education", "instruction"],
    "deaf": ["special education", "speech", "audiolog"],
    "special education": ["special education"],
    "therapist": ["therapist", "therapy", "counselor"],
    "engineer": ["engineer"],
    "engineering": ["engineer"],
    "pharmacist": ["pharmac"],
    "pharmacy": ["pharmac"],
    "pre-pharm": ["pharmac"],
    "prepharm": ["pharmac"],
    "architect": ["architect"],
    "psychologist": ["psycholog"],
    "psychology": ["psycholog"],
    "accountant": ["account", "auditor", "financial"],
    "accounting": ["account", "auditor", "financial"],
    # Group A — advanced-degree intents (ride the doctoral-preference rule)
    "slp": ["speech", "language pathologist", "audiolog"],
    "speech pathologist": ["speech", "language pathologist", "audiolog"],
    "speech-language pathologist": ["speech", "language pathologist", "audiolog"],
    "speech language pathologist": ["speech", "language pathologist", "audiolog"],
    "speech therapy": ["speech", "language pathologist", "audiolog"],
    "physical therapist": ["physical therap"],
    "physical therapy": ["physical therap"],
    "pre-pt": ["physical therap"],
    "prept": ["physical therap"],
    "dpt": ["physical therap"],
    # Group B — recognized intents that map to non-doctoral credentials.
    # Listed in SYNONYM_MAP so the candidate pool surfaces them, but the
    # SYSTEM_PROMPT rule 3 explicitly tells Gemma NOT to apply the
    # doctoral-preference clause to these.
    "librarian": ["librar"],
    "library science": ["librar"],
    "mlis": ["librar"],
    "music therapist": ["music therap", "therapist"],
    "music therapy": ["music therap", "therapist"],
    "mt-bc": ["music therap", "therapist"],
    "mortician": ["morticia", "funeral"],
    "funeral director": ["morticia", "funeral"],
    "mortuary": ["morticia", "funeral"],
    "mortuary science": ["morticia", "funeral"],
}

EXPAND_SOCS_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "expand_socs",
        "description": (
            "Pick up to 5 SOC codes from the candidate pool that the "
            "student's stated career intent demands but the BLS CIP-SOC "
            "crosswalk did not return. Picks must be from the pool only."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "soc_codes": {
                    "type": "array",
                    "items": {"type": "string", "pattern": r"^\d{2}-\d{4}$"},
                    "minItems": 0,
                    "maxItems": 5,
                    "description": (
                        "SOC codes from the candidate pool that should be "
                        "added because they directly match the student's "
                        "stated intent."
                    ),
                },
                "rationale": {
                    "type": "string",
                    "description": "One sentence explaining the picks.",
                },
            },
            "required": ["soc_codes", "rationale"],
        },
    },
}

SYSTEM_PROMPT = """\
You expand a student's career-search SOC list when the BLS CIP-SOC \
crosswalk doesn't return SOCs the student's stated intent demands.

You will receive:
- The student's intent keywords (e.g., "pre-med", "doctor").
- The existing SOC list from the crosswalk (do NOT re-pick these).
- A candidate pool of SOCs in the format:
    SOC_CODE | Title | Major Group | Education Level

Call expand_socs with:
- soc_codes: up to 5 SOC codes from the candidate pool that directly \
match the student's intent and are NOT already in the existing list. \
Use the XX-XXXX format exactly (e.g., 29-1229, 25-2052).
- rationale: one sentence explaining the picks.

Selection rules:
1. Only pick SOCs from the candidate pool. Never invent codes.
2. If the student's intent implies an advanced degree — keywords like \
"pre-med", "doctor", "physician", "pre-vet", "veterinarian", \
"dentist", "pre-law", "attorney", "pharmacist", "pre-pharm", \
"speech pathologist", "slp", "physical therapist", "pre-pt", "dpt" \
— prefer SOCs requiring a doctoral or professional degree over \
associate's or bachelor's-level SOCs.
3. Some intent keywords map to non-doctoral standalone credentials. \
For these — "librarian", "mlis", "music therapist", "mt-bc", \
"mortician", "funeral director" — pick the candidate SOC matching \
the profession but do NOT prefer doctoral-level SOCs. Morticians \
(39-4031) require an associate's; librarians (25-4022) require a \
master's; music therapists (29-1129) typically a bachelor's plus \
certification. Match the candidate at its real education level.
4. If no candidate SOC genuinely matches the intent, return an empty \
soc_codes array (do not force picks to fill the cap).
5. Do not pick SOCs that are semantically redundant with those already \
in the existing list (same role at a different level is fine; \
exact duplicates are not).\
"""


def expand_socs(
    intent_keywords: list[str],
    base_socs: list[str],
    cip_family: str,
    *,
    program_name: str = "",
    base_soc_titles: list[str] | None = None,
    query_fn: Callable[..., list[dict[str, Any]]] | None = None,
) -> list[str]:
    """Return the union of base_socs + up to 5 Gemma-picked SOCs.

    Triggers expansion when EITHER:
      (a) intent_keywords is non-empty, OR
      (b) the program name shares no significant tokens with any
          base SOC title (the "program-negating crosswalk" case).

    Pure pass-through when neither condition holds (no Gemma call).
    Falls back to base_socs unchanged on any Gemma error or parse
    failure.
    """
    derived_keywords = list(intent_keywords)
    if not derived_keywords and program_name and base_soc_titles is not None:
        if _program_negates_crosswalk(program_name, base_soc_titles):
            derived_keywords = _tokens_from_program_name(program_name)

    if not derived_keywords:
        return base_socs

    try:
        candidate_pool = _build_candidate_pool(
            derived_keywords, base_socs, cip_family, query_fn=query_fn,
        )
    except Exception:
        logger.warning("soc_expansion: candidate pool build failed", exc_info=True)
        return base_socs

    if not candidate_pool:
        logger.debug(
            "soc_expansion: empty candidate pool for keywords=%s", derived_keywords,
        )
        return base_socs

    picks, reason = _ask_gemma_for_picks(
        derived_keywords, base_socs, candidate_pool, cip_family,
    )

    if not picks:
        return base_socs

    valid_picks = [s for s in picks if s in candidate_pool and s not in base_socs]
    valid_picks = valid_picks[:EXPANSION_CAP]

    if not valid_picks and picks:
        reason = "all_picks_filtered"

    final_reason = reason if valid_picks else (reason or "no_matches_in_pool")
    logger.info(
        "soc_expansion: keywords=%s pool_size=%d picked=%d valid=%d reason=%s",
        derived_keywords,
        len(candidate_pool),
        len(picks),
        len(valid_picks),
        final_reason,
    )

    return list(dict.fromkeys(base_socs + valid_picks))


def _program_negates_crosswalk(
    program_name: str, base_soc_titles: list[str],
) -> bool:
    """True when the program name shares no significant non-negated
    tokens with ANY base SOC title."""
    prog_tokens = _tokens_from_program_name(program_name)
    if not prog_tokens:
        return False

    negation_prefixes = ("except", "excluding", "non-", "other than")
    for title in base_soc_titles:
        title_lower = title.lower()
        for token in prog_tokens:
            idx = title_lower.find(token)
            if idx < 0:
                continue
            preceding = title_lower[:idx].strip().rstrip(",").strip()
            if any(preceding.endswith(neg) for neg in negation_prefixes):
                continue
            return False
    return True


def _tokens_from_program_name(program_name: str) -> list[str]:
    """Lowercase content tokens from the program name."""
    raw = re.sub(r"[^a-zA-Z\s]", " ", program_name.lower())
    tokens = raw.split()
    return [
        t for t in tokens
        if t not in _STOPWORDS
        and t not in _CIP_ADMIN_TERMS
        and len(t) > 2
    ]


def _expand_keywords(keywords: list[str]) -> list[str]:
    """Expand keywords via the synonym map."""
    expanded = set()
    for kw in keywords:
        kw_lower = kw.lower().strip()
        expanded.add(kw_lower)
        if kw_lower in SYNONYM_MAP:
            expanded.update(SYNONYM_MAP[kw_lower])
    return list(expanded)


def _build_candidate_pool(
    intent_keywords: list[str],
    base_socs: list[str],
    cip_family: str,
    *,
    query_fn: Callable[..., list[dict[str, Any]]] | None = None,
) -> dict[str, dict[str, str]]:
    """Pre-filter consumable.occupation_profiles to ~30 SOC candidates.

    Uses synonym bridging before substring match. Queries via the
    provided query_fn (which should be QueryEngine.query_sql or
    equivalent).
    """
    if query_fn is None:
        logger.warning("soc_expansion: no query_fn provided, returning empty pool")
        return {}

    expanded = _expand_keywords(intent_keywords)
    if not expanded:
        return {}

    try:
        rows = query_fn(
            "SELECT soc_code, occupation_title, soc_major_group_name, "
            "education_level_name FROM consumable_occupation_profiles",
            {},
        )
    except Exception:
        logger.warning("soc_expansion: occupation_profiles query failed", exc_info=True)
        return {}

    base_set = set(base_socs)
    pool: dict[str, dict[str, str]] = {}

    for row in rows:
        soc = str(row.get("soc_code", ""))
        if not soc or soc in base_set:
            continue
        title = str(row.get("occupation_title", "")).lower()
        group = str(row.get("soc_major_group_name", "")).lower()
        search_text = f"{title} {group}"

        if any(kw in search_text for kw in expanded):
            pool[soc] = {
                "title": str(row.get("occupation_title", "")),
                "major_group": str(row.get("soc_major_group_name", "")),
                "education_level": str(row.get("education_level_name", "")),
            }
            if len(pool) >= CANDIDATE_POOL_CAP:
                break

    return pool


def _format_candidate_pool(pool: dict[str, dict[str, str]]) -> str:
    """Format the candidate pool as a pipe-delimited table."""
    lines = []
    for soc, info in pool.items():
        lines.append(
            f"{soc} | {info['title']} | {info['major_group']} | "
            f"{info['education_level']}"
        )
    return "\n".join(lines)


def _ask_gemma_for_picks(
    intent_keywords: list[str],
    base_socs: list[str],
    candidate_pool: dict[str, dict[str, str]],
    cip_family: str,
) -> tuple[list[str], str]:
    """Call Gemma with tools=[expand_socs] and return (picked_socs, reason).

    Returns ([], reason) on failure. Caller filters against the pool.
    """
    pool_text = _format_candidate_pool(candidate_pool)
    base_list = ", ".join(base_socs)

    user_msg = (
        f"Student intent keywords: {', '.join(intent_keywords)}\n\n"
        f"Already in the student's list (do not pick these):\n"
        f"{base_list}\n\n"
        f"Candidate pool (pick from these only):\n"
        f"{pool_text}"
    )

    try:
        result = gemma_client.generate_with_tools(
            system=SYSTEM_PROMPT,
            user=user_msg,
            tools=[EXPAND_SOCS_TOOL],
            tool_choice="required",
            max_tokens=600,
            temperature=0.0,
            extra={
                "call_site": "soc_expansion",
                "intent_keywords": intent_keywords,
                "candidate_pool_size": len(candidate_pool),
            },
        )
    except Exception:
        logger.warning("soc_expansion: Gemma call failed", exc_info=True)
        return [], "gemma_failure"

    if result is None:
        return [], "gemma_failure"

    args = result.get("arguments", {})
    soc_codes = args.get("soc_codes", [])

    if not isinstance(soc_codes, list):
        return [], "gemma_failure"

    soc_pattern = re.compile(r"^\d{2}-\d{4}$")
    valid = [s for s in soc_codes if isinstance(s, str) and soc_pattern.match(s)]

    if not valid:
        return [], "no_matches_in_pool"

    return valid, "expanded"
