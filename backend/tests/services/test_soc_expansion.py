"""Tests for SOC expansion via Gemma function calling.

Validates every code path in ``soc_expansion.expand_socs``:

- Pass-through (no intent, aligned crosswalk)
- Program-negating crosswalk triggers expansion without explicit intent
- Intent keywords take precedence over program-name fallback
- Gemma picks appended, filtered, capped, deduped
- Gemma failure falls back gracefully
- Synonym bridging surfaces correct candidates
- Candidate pool excludes base SOCs and respects cap

All tests mock ``gemma_client.generate_with_tools`` so no real
Gemma/Ollama/OpenRouter calls are made. Candidate pool tests provide
a ``query_fn`` mock returning occupation_profiles rows.
"""

from __future__ import annotations

from unittest.mock import patch

from app.services import soc_expansion
from app.services.soc_expansion import (
    CANDIDATE_POOL_CAP,
    EXPANSION_CAP,
    _build_candidate_pool,
    _expand_keywords,
    _program_negates_crosswalk,
    _tokens_from_program_name,
    expand_socs,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Realistic occupation_profiles rows for query_fn mocks.
_DOC = "Doctoral or professional degree"
_BACH = "Bachelor's degree"
_MAST = "Master's degree"
_HEALTH = "Healthcare Practitioners"
_EDU = "Educational Instruction and Library"

_OCCUPATION_ROWS = [
    {
        "soc_code": "29-1228",
        "occupation_title": "Physicians, All Other",
        "soc_major_group_name": _HEALTH,
        "education_level_name": _DOC,
    },
    {
        "soc_code": "29-1241",
        "occupation_title": "Ophthalmologists, Except Pediatric",
        "soc_major_group_name": _HEALTH,
        "education_level_name": _DOC,
    },
    {
        "soc_code": "29-1243",
        "occupation_title": "Pediatric Surgeons",
        "soc_major_group_name": _HEALTH,
        "education_level_name": _DOC,
    },
    {
        "soc_code": "25-2052",
        "occupation_title": (
            "Special Education Teachers, Kindergarten and Elementary School"
        ),
        "soc_major_group_name": _EDU,
        "education_level_name": _BACH,
    },
    {
        "soc_code": "25-2053",
        "occupation_title": "Special Education Teachers, Middle School",
        "soc_major_group_name": _EDU,
        "education_level_name": _BACH,
    },
    {
        "soc_code": "25-2054",
        "occupation_title": "Special Education Teachers, Secondary School",
        "soc_major_group_name": _EDU,
        "education_level_name": _BACH,
    },
    {
        "soc_code": "25-2058",
        "occupation_title": "Special Education Teachers, All Other",
        "soc_major_group_name": _EDU,
        "education_level_name": _BACH,
    },
    {
        "soc_code": "11-1021",
        "occupation_title": "General and Operations Managers",
        "soc_major_group_name": "Management",
        "education_level_name": _BACH,
    },
    {
        "soc_code": "13-2011",
        "occupation_title": "Accountants and Auditors",
        "soc_major_group_name": "Business and Financial",
        "education_level_name": _BACH,
    },
    {
        "soc_code": "15-1252",
        "occupation_title": "Software Developers",
        "soc_major_group_name": "Computer and Mathematical",
        "education_level_name": _BACH,
    },
    {
        "soc_code": "19-1042",
        "occupation_title": "Medical Scientists, Except Epidemiologists",
        "soc_major_group_name": "Life, Physical, and Social Science",
        "education_level_name": _DOC,
    },
    {
        "soc_code": "21-1012",
        "occupation_title": (
            "Educational, Guidance, and Career Counselors and Advisors"
        ),
        "soc_major_group_name": "Community and Social Service",
        "education_level_name": _MAST,
    },
    {
        "soc_code": "29-1131",
        "occupation_title": "Veterinarians",
        "soc_major_group_name": _HEALTH,
        "education_level_name": _DOC,
    },
]


def _make_query_fn(rows: list[dict] | None = None):
    """Return a callable that mimics QueryEngine.query_sql."""
    data = rows if rows is not None else _OCCUPATION_ROWS
    def query_fn(sql: str, params: dict):
        return data
    return query_fn


def _make_gemma_tool_result(soc_codes: list[str], rationale: str = "test") -> dict:
    """Return the dict that generate_with_tools returns on success."""
    return {
        "name": "expand_socs",
        "arguments": {"soc_codes": soc_codes, "rationale": rationale},
    }


# ---------------------------------------------------------------------------
# P0: Pass-through — empty intent + aligned crosswalk
# ---------------------------------------------------------------------------


class TestPassThrough:
    def test_empty_intent_aligned_crosswalk_returns_base_socs_no_gemma_call(self):
        """Empty keywords + program name aligns with SOC titles = pure pass-through.
        Gemma must never be called."""
        base_socs = ["19-1042", "25-1042"]
        # Program name tokens overlap with SOC title tokens ("medical" in
        # "Medical Scientists"), so the crosswalk is NOT negated.
        with patch.object(
            soc_expansion.gemma_client, "generate_with_tools"
        ) as mock_gemma:
            result = expand_socs(
                intent_keywords=[],
                base_socs=base_socs,
                cip_family="26",
                program_name="Medical Biology",
                base_soc_titles=["Medical Scientists, Except Epidemiologists"],
                query_fn=_make_query_fn(),
            )
        assert result == base_socs
        mock_gemma.assert_not_called()

    def test_no_program_name_no_intent_passes_through(self):
        """No intent keywords and no program name = pass-through."""
        base_socs = ["19-1042"]
        with patch.object(
            soc_expansion.gemma_client, "generate_with_tools"
        ) as mock_gemma:
            result = expand_socs(
                intent_keywords=[],
                base_socs=base_socs,
                cip_family="26",
            )
        assert result == base_socs
        mock_gemma.assert_not_called()


# ---------------------------------------------------------------------------
# P0: Program-negating crosswalk triggers expansion without intent
# ---------------------------------------------------------------------------


class TestProgramNegatingCrosswalk:
    def test_program_negating_crosswalk_triggers_expansion_without_intent(self):
        """When no program-name token appears un-negated in any SOC title,
        the crosswalk is deemed negating and expansion triggers even
        though intent_keywords is empty.

        The negation check is per-token: it finds the token via substring
        search and checks whether the immediately preceding text ends
        with a negation prefix like 'except'. Critically, in the title
        'Except Special Education', the token 'education' is preceded by
        'except special' (which does NOT end with 'except'), so
        'education' reads as un-negated. To truly negate, program tokens
        must either not appear at all or each individually be preceded
        by a negation prefix.

        We use titles where program-name tokens simply don't appear
        (different terminology), which is the realistic case for many
        crosswalk mismatches.
        """
        base_socs = ["25-2031"]
        # These titles use different terminology than the program name
        # tokens ("deaf", "teaching"). No substring of "deaf" or "teaching"
        # appears, so the function sees no un-negated overlap -> True.
        soc_titles = [
            "Secondary School Teachers, Except Special and Career/Technical",
            "Middle School Teachers, Except Special and Career/Technical",
        ]
        with patch.object(
            soc_expansion.gemma_client, "generate_with_tools",
            return_value=_make_gemma_tool_result(["25-2052", "25-2058"]),
        ) as mock_gemma:
            result = expand_socs(
                intent_keywords=[],
                base_socs=base_socs,
                cip_family="13",
                program_name="Deaf Education Teaching",
                base_soc_titles=soc_titles,
                query_fn=_make_query_fn(),
            )
        # Gemma WAS called because the crosswalk negated.
        mock_gemma.assert_called_once()
        # The special-ed SOCs got appended.
        assert "25-2052" in result
        assert "25-2058" in result
        # Original base SOCs preserved.
        assert result[0] == "25-2031"

    def test_program_negates_crosswalk_detects_absent_tokens(self):
        """When program-name tokens don't appear in any SOC title at all,
        _program_negates_crosswalk returns True (no overlap means
        crosswalk is misaligned with the program)."""
        # "deaf" does not appear anywhere in these titles.
        assert _program_negates_crosswalk(
            "Deaf Education Teaching",
            ["Secondary School Teachers, Except Special and Career/Technical"],
        ) is True

    def test_program_negates_crosswalk_negation_prefix_works(self):
        """When a token is found but preceded by 'except', it is negated."""
        # "special" appears at idx where preceding text ends with "except".
        # "deaf" doesn't appear at all. So no un-negated matches -> True.
        assert _program_negates_crosswalk(
            "Special Deaf Studies",
            ["Teachers, Except Special"],
        ) is True

    def test_program_negates_not_triggered_when_token_appears_without_negation(self):
        """When at least one program token appears in a title WITHOUT a
        negation prefix, the crosswalk is NOT negated."""
        # "education" appears in "Career/Technical Education" without negation,
        # even though "special" is negated by "except".
        assert _program_negates_crosswalk(
            "Special Education and Teaching",
            [
                "Secondary School Teachers, Except Special"
                " and Career/Technical Education"
            ],
        ) is False

    def test_program_does_not_negate_when_tokens_match(self):
        """When program tokens are found un-negated via substring match,
        no negation is detected. Note: 'biology' is NOT a substring of
        'biological', so this title set actually DOES negate."""
        # "biology" is NOT found as a substring in "biological scientists"
        # (find returns -1), so the function sees no un-negated match.
        # We must use a title that actually CONTAINS "biology" as a substring.
        assert _program_negates_crosswalk(
            "Biology, General",
            ["Biology Teachers, Postsecondary", "Medical Scientists"],
        ) is False

    def test_program_negates_empty_program_name(self):
        """Empty program name has no tokens — cannot negate."""
        assert _program_negates_crosswalk("", ["Some Title"]) is False


# ---------------------------------------------------------------------------
# P0: Intent keywords take precedence
# ---------------------------------------------------------------------------


class TestIntentPrecedence:
    def test_intent_keywords_take_precedence_over_program_name_fallback(self):
        """When intent_keywords is non-empty, those are used directly
        regardless of whether the crosswalk is negated."""
        base_socs = ["19-1042"]
        with patch.object(
            soc_expansion.gemma_client, "generate_with_tools",
            return_value=_make_gemma_tool_result(["29-1228"]),
        ) as mock_gemma:
            result = expand_socs(
                intent_keywords=["pre-med", "doctor"],
                base_socs=base_socs,
                cip_family="26",
                program_name="Biology, General",
                base_soc_titles=["Biological Scientists, All Other"],
                query_fn=_make_query_fn(),
            )
        mock_gemma.assert_called_once()
        # Verify the user message sent to Gemma contains "pre-med" (the
        # intent keyword), not "biology" (the program-name fallback).
        call_kwargs = mock_gemma.call_args
        user_msg = call_kwargs.kwargs.get("user", "") or call_kwargs[1].get("user", "")
        assert "pre-med" in user_msg
        assert "29-1228" in result


# ---------------------------------------------------------------------------
# P0: Gemma picks — added, filtered, capped, deduped
# ---------------------------------------------------------------------------


class TestGemmaPickProcessing:
    def test_gemma_picks_added_to_base_socs(self):
        """Mocked Gemma returns valid SOCs that exist in candidate pool;
        they get appended to base_socs.

        29-1228 (Physicians) and 29-1243 (Pediatric Surgeons) both match
        the 'doctor' synonym expansion ('physician', 'surgeon', 'medical').
        29-1241 (Ophthalmologists) does NOT match those keywords and thus
        won't be in the candidate pool — so we use SOCs that will be.
        """
        base_socs = ["19-1042"]
        with patch.object(
            soc_expansion.gemma_client, "generate_with_tools",
            return_value=_make_gemma_tool_result(["29-1228", "29-1243"]),
        ):
            result = expand_socs(
                intent_keywords=["doctor"],
                base_socs=base_socs,
                cip_family="26",
                query_fn=_make_query_fn(),
            )
        assert result == ["19-1042", "29-1228", "29-1243"]

    def test_gemma_picks_outside_candidate_pool_filtered(self):
        """SOCs returned by Gemma that are NOT in the candidate pool get dropped."""
        base_socs = ["19-1042"]
        with patch.object(
            soc_expansion.gemma_client, "generate_with_tools",
            return_value=_make_gemma_tool_result(["99-9999"]),
        ):
            result = expand_socs(
                intent_keywords=["doctor"],
                base_socs=base_socs,
                cip_family="26",
                query_fn=_make_query_fn(),
            )
        # 99-9999 is not in the pool, so result is just base_socs.
        assert result == base_socs

    def test_expansion_capped_at_five(self):
        """Even if Gemma returns 8 valid SOCs, only the first 5 are appended."""
        # Build a pool with 8+ SOCs that match "engineer".
        engineer_rows = [
            {"soc_code": f"17-20{i:02d}", "occupation_title": f"Engineer Type {i}",
             "soc_major_group_name": "Architecture and Engineering",
             "education_level_name": "Bachelor's degree"}
            for i in range(10)
        ]
        all_rows = _OCCUPATION_ROWS + engineer_rows

        eight_socs = [f"17-20{i:02d}" for i in range(8)]
        base_socs = ["11-1021"]

        with patch.object(
            soc_expansion.gemma_client, "generate_with_tools",
            return_value=_make_gemma_tool_result(eight_socs),
        ):
            result = expand_socs(
                intent_keywords=["engineer"],
                base_socs=base_socs,
                cip_family="14",
                query_fn=_make_query_fn(all_rows),
            )
        appended = [s for s in result if s != "11-1021"]
        assert len(appended) == EXPANSION_CAP
        assert len(appended) == 5

    def test_duplicate_picks_deduped(self):
        """If Gemma picks a SOC already in base_socs, it is not duplicated.

        Uses 29-1243 (Pediatric Surgeons) as the new pick since it matches
        the 'doctor' synonym expansion and will be in the candidate pool.
        """
        base_socs = ["29-1228", "19-1042"]
        # Gemma returns 29-1228 (already in base) + 29-1243 (new).
        with patch.object(
            soc_expansion.gemma_client, "generate_with_tools",
            return_value=_make_gemma_tool_result(["29-1228", "29-1243"]),
        ):
            result = expand_socs(
                intent_keywords=["doctor"],
                base_socs=base_socs,
                cip_family="26",
                query_fn=_make_query_fn(),
            )
        # 29-1228 appears exactly once (from base), 29-1243 appended.
        assert result.count("29-1228") == 1
        assert "29-1243" in result
        assert result == ["29-1228", "19-1042", "29-1243"]


# ---------------------------------------------------------------------------
# P0: Gemma failure fallback
# ---------------------------------------------------------------------------


class TestGemmaFailure:
    def test_gemma_failure_returns_base_socs(self):
        """When Gemma raises an exception, expand_socs returns base_socs
        unchanged. No exception propagates to the caller."""
        base_socs = ["19-1042", "25-1042"]
        with patch.object(
            soc_expansion.gemma_client, "generate_with_tools",
            side_effect=RuntimeError("Ollama is down"),
        ):
            result = expand_socs(
                intent_keywords=["doctor"],
                base_socs=base_socs,
                cip_family="26",
                query_fn=_make_query_fn(),
            )
        assert result == base_socs

    def test_gemma_returns_none_returns_base_socs(self):
        """When Gemma returns None (no tool call), expand_socs returns base_socs."""
        base_socs = ["19-1042"]
        with patch.object(
            soc_expansion.gemma_client, "generate_with_tools",
            return_value=None,
        ):
            result = expand_socs(
                intent_keywords=["doctor"],
                base_socs=base_socs,
                cip_family="26",
                query_fn=_make_query_fn(),
            )
        assert result == base_socs

    def test_gemma_returns_malformed_arguments(self):
        """When Gemma returns a result without soc_codes, falls back."""
        base_socs = ["19-1042"]
        with patch.object(
            soc_expansion.gemma_client, "generate_with_tools",
            return_value={"name": "expand_socs", "arguments": {"rationale": "oops"}},
        ):
            result = expand_socs(
                intent_keywords=["doctor"],
                base_socs=base_socs,
                cip_family="26",
                query_fn=_make_query_fn(),
            )
        assert result == base_socs

    def test_query_fn_failure_returns_base_socs(self):
        """When the candidate pool query_fn raises, fall back to base_socs."""
        base_socs = ["19-1042"]
        def exploding_query(sql, params):
            raise ConnectionError("DuckDB is unavailable")

        with patch.object(
            soc_expansion.gemma_client, "generate_with_tools"
        ) as mock_gemma:
            result = expand_socs(
                intent_keywords=["doctor"],
                base_socs=base_socs,
                cip_family="26",
                query_fn=exploding_query,
            )
        assert result == base_socs
        mock_gemma.assert_not_called()


# ---------------------------------------------------------------------------
# P0: Synonym bridging / canonical broken cases
# ---------------------------------------------------------------------------


class TestSynonymBridging:
    def test_pre_med_biology_surfaces_physicians(self):
        """With intent_keywords=["pre-med", "doctor"], the candidate pool
        must contain physician/surgeon SOCs via synonym bridging."""
        pool = _build_candidate_pool(
            ["pre-med", "doctor"],
            base_socs=[],
            cip_family="26",
            query_fn=_make_query_fn(),
        )
        # SYNONYM_MAP maps "pre-med" and "doctor" to "physician", "surgeon", "medical".
        # Our fixture has 29-1228 (Physicians) and 29-1243 (Pediatric Surgeons).
        assert "29-1228" in pool, "Physicians should be in candidate pool"
        assert "29-1243" in pool, "Surgeons should be in candidate pool"

    def test_deaf_ed_special_education_surfaces_special_ed_teachers(self):
        """The canonical broken case: 'deaf education' intent must surface
        special education teacher SOCs."""
        pool = _build_candidate_pool(
            ["deaf education", "special education", "teacher"],
            base_socs=[],
            cip_family="13",
            query_fn=_make_query_fn(),
        )
        special_ed_socs = {"25-2052", "25-2053", "25-2054", "25-2058"}
        found = special_ed_socs & set(pool.keys())
        assert len(found) >= 1, (
            f"Expected at least one special-ed teacher SOC in pool, "
            f"got: {list(pool.keys())}"
        )

    def test_synonym_map_bridges_student_language(self):
        """Verify the synonym map expands common student-language terms
        into BLS-language terms."""
        # "pre-med" -> physician, surgeon, medical
        expanded = _expand_keywords(["pre-med"])
        assert "physician" in expanded
        assert "surgeon" in expanded
        assert "medical" in expanded
        assert "pre-med" in expanded  # original preserved

        # "deaf" -> special education, speech, audiolog
        expanded_deaf = _expand_keywords(["deaf"])
        assert "special education" in expanded_deaf
        assert "speech" in expanded_deaf

        # "lawyer" -> attorney, legal, judicial
        expanded_law = _expand_keywords(["lawyer"])
        assert "attorney" in expanded_law
        assert "legal" in expanded_law

    def test_expand_keywords_unknown_term_preserved(self):
        """Terms not in SYNONYM_MAP are preserved as-is."""
        expanded = _expand_keywords(["data science"])
        assert "data science" in expanded


# ---------------------------------------------------------------------------
# P2: Candidate pool mechanics
# ---------------------------------------------------------------------------


class TestCandidatePool:
    def test_candidate_pool_excludes_base_socs(self):
        """SOCs already in base_socs must not appear in the candidate pool."""
        base_socs = ["29-1228"]  # Physicians
        pool = _build_candidate_pool(
            ["doctor"],
            base_socs=base_socs,
            cip_family="26",
            query_fn=_make_query_fn(),
        )
        assert "29-1228" not in pool

    def test_candidate_pool_capped_at_thirty(self):
        """Even with many matching SOCs, the pool cannot exceed CANDIDATE_POOL_CAP."""
        # Generate 50 rows that all match "engineer".
        many_rows = [
            {"soc_code": f"17-{i:04d}", "occupation_title": f"Engineer Type {i}",
             "soc_major_group_name": "Architecture and Engineering",
             "education_level_name": "Bachelor's degree"}
            for i in range(50)
        ]
        pool = _build_candidate_pool(
            ["engineer"],
            base_socs=[],
            cip_family="14",
            query_fn=_make_query_fn(many_rows),
        )
        assert len(pool) <= CANDIDATE_POOL_CAP
        assert len(pool) == CANDIDATE_POOL_CAP  # should hit the cap exactly

    def test_candidate_pool_no_query_fn_returns_empty(self):
        """When no query_fn is provided, the pool is empty."""
        pool = _build_candidate_pool(
            ["doctor"],
            base_socs=[],
            cip_family="26",
            query_fn=None,
        )
        assert pool == {}

    def test_candidate_pool_empty_keywords_returns_empty(self):
        """When expanded keywords are empty, the pool is empty."""
        pool = _build_candidate_pool(
            [],
            base_socs=[],
            cip_family="26",
            query_fn=_make_query_fn(),
        )
        assert pool == {}

    def test_empty_candidate_pool_returns_base_socs(self):
        """When no candidates match, expand_socs returns base_socs."""
        base_socs = ["19-1042"]
        # Query fn returns rows but none match the keywords.
        no_match_rows = [
            {"soc_code": "99-0001", "occupation_title": "Unicorn Wrangler",
             "soc_major_group_name": "Fantasy", "education_level_name": "None"},
        ]
        with patch.object(
            soc_expansion.gemma_client, "generate_with_tools"
        ) as mock_gemma:
            result = expand_socs(
                intent_keywords=["doctor"],
                base_socs=base_socs,
                cip_family="26",
                query_fn=_make_query_fn(no_match_rows),
            )
        assert result == base_socs
        mock_gemma.assert_not_called()


# ---------------------------------------------------------------------------
# Token extraction
# ---------------------------------------------------------------------------


class TestTokenExtraction:
    def test_tokens_from_program_name_strips_stopwords(self):
        tokens = _tokens_from_program_name("Biology, General and Other Studies")
        # "general", "other", "studies" are CIP admin terms; "and" is a stopword.
        assert "biology" in tokens
        assert "general" not in tokens
        assert "other" not in tokens
        assert "and" not in tokens

    def test_tokens_from_program_name_short_tokens_dropped(self):
        """Tokens with 2 or fewer chars are dropped."""
        tokens = _tokens_from_program_name("IT and CS")
        # "it" is a stopword, "cs" is 2 chars -> dropped
        assert "cs" not in tokens

    def test_tokens_from_program_name_empty(self):
        assert _tokens_from_program_name("") == []


# ---------------------------------------------------------------------------
# Bundle 5: Postgrad-intent extension (post-100-build-test-fixes-bundle §4)
#
# Group A: pharmacist/pre-pharm, slp/speech pathologist, physical
# therapist/pre-pt/dpt — all advanced-degree credentials. They ride the
# SYSTEM_PROMPT's doctoral-preference clause.
#
# Group B: librarian/mlis (master's), music therapist/mt-bc (bachelor's
# + cert), mortician/funeral director (associate's). They surface in
# the candidate pool but the SYSTEM_PROMPT explicitly tells Gemma NOT
# to apply doctoral-preference to them.
#
# These tests focus on the candidate pool — proving that the synonym
# bridging routes each intent keyword to the right BLS SOC. The
# doctoral-preference clause is a prompt-level concern (Gemma's
# behavior), so the negative tests assert that Group B SOCs surface
# at their REAL education tier, not over-promoted.
# ---------------------------------------------------------------------------


# Realistic occupation_profiles rows for the Group A + Group B SOCs.
_POSTGRAD_OCCUPATION_ROWS = [
    # Group A — advanced-degree credentials
    {
        "soc_code": "29-1051",
        "occupation_title": "Pharmacists",
        "soc_major_group_name": "Healthcare Practitioners and Technical",
        "education_level_name": "Doctoral or professional degree",
    },
    {
        "soc_code": "29-1127",
        "occupation_title": "Speech-Language Pathologists",
        "soc_major_group_name": "Healthcare Practitioners and Technical",
        "education_level_name": "Master's degree",
    },
    {
        "soc_code": "29-1123",
        "occupation_title": "Physical Therapists",
        "soc_major_group_name": "Healthcare Practitioners and Technical",
        "education_level_name": "Doctoral or professional degree",
    },
    # Group B — non-doctoral credentials
    {
        "soc_code": "25-4022",
        "occupation_title": "Librarians and Media Collections Specialists",
        "soc_major_group_name": "Educational Instruction and Library",
        "education_level_name": "Master's degree",
    },
    {
        "soc_code": "29-1129",
        "occupation_title": "Therapists, All Other",
        "soc_major_group_name": "Healthcare Practitioners and Technical",
        "education_level_name": "Bachelor's degree",
    },
    {
        "soc_code": "39-4031",
        "occupation_title": "Morticians, Undertakers, and Funeral Arrangers",
        "soc_major_group_name": "Personal Care and Service",
        "education_level_name": "Associate's degree",
    },
    # Decoys — doctoral SOCs that should NOT be preferred for Group B
    {
        "soc_code": "29-1228",
        "occupation_title": "Physicians, All Other",
        "soc_major_group_name": "Healthcare Practitioners and Technical",
        "education_level_name": "Doctoral or professional degree",
    },
    {
        "soc_code": "25-1011",
        "occupation_title": "Business Teachers, Postsecondary",
        "soc_major_group_name": "Educational Instruction and Library",
        "education_level_name": "Doctoral or professional degree",
    },
]


def _make_postgrad_query_fn():
    return _make_query_fn(_POSTGRAD_OCCUPATION_ROWS)


class TestGroupAPostgradIntents:
    """Group A intents must surface their target SOC in the candidate pool.

    The synonym map routes 'pharmacy' → 'pharmac', 'slp' →
    'speech'/'language pathologist'/'audiolog', etc. The candidate-pool
    builder does a case-insensitive substring match against
    occupation_title + soc_major_group_name.
    """

    def test_pharmacy_intent_surfaces_pharmacist_soc(self):
        """intent_keywords=['pharmacy'] → 29-1051 (Pharmacists) is in
        the candidate pool. Confirms the synonym 'pharmacy' → 'pharmac'
        bridging fires."""
        pool = _build_candidate_pool(
            ["pharmacy"],
            base_socs=[],
            cip_family="51",
            query_fn=_make_postgrad_query_fn(),
        )
        assert "29-1051" in pool, (
            f"Pharmacists SOC 29-1051 must surface for the 'pharmacy' "
            f"intent; got pool {sorted(pool.keys())}"
        )
        assert pool["29-1051"]["education_level"] == (
            "Doctoral or professional degree"
        )

    def test_pharmacy_intent_pre_pharm_alias_surfaces_same_soc(self):
        """The 'pre-pharm' alias rides the same synonym entry."""
        pool = _build_candidate_pool(
            ["pre-pharm"],
            base_socs=[],
            cip_family="26",
            query_fn=_make_postgrad_query_fn(),
        )
        assert "29-1051" in pool

    def test_slp_intent_surfaces_slp_soc(self):
        """intent_keywords=['slp'] → 29-1127 (Speech-Language
        Pathologists) is in the candidate pool."""
        pool = _build_candidate_pool(
            ["slp"],
            base_socs=[],
            cip_family="51",
            query_fn=_make_postgrad_query_fn(),
        )
        assert "29-1127" in pool, (
            f"SLP SOC 29-1127 must surface for the 'slp' intent; got "
            f"pool {sorted(pool.keys())}"
        )

    def test_slp_intent_speech_pathologist_synonym_surfaces_same_soc(self):
        """'speech pathologist' is the full-name alias for the same SOC."""
        pool = _build_candidate_pool(
            ["speech pathologist"],
            base_socs=[],
            cip_family="51",
            query_fn=_make_postgrad_query_fn(),
        )
        assert "29-1127" in pool

    def test_physical_therapy_intent_surfaces_pt_soc(self):
        """intent_keywords=['physical therapy'] → 29-1123 (Physical
        Therapists) is in the candidate pool."""
        pool = _build_candidate_pool(
            ["physical therapy"],
            base_socs=[],
            cip_family="51",
            query_fn=_make_postgrad_query_fn(),
        )
        assert "29-1123" in pool, (
            f"Physical Therapists SOC 29-1123 must surface; got pool "
            f"{sorted(pool.keys())}"
        )

    def test_physical_therapy_intent_dpt_alias_surfaces_same_soc(self):
        """'dpt' (Doctor of Physical Therapy) is the credential alias."""
        pool = _build_candidate_pool(
            ["dpt"],
            base_socs=[],
            cip_family="51",
            query_fn=_make_postgrad_query_fn(),
        )
        assert "29-1123" in pool


class TestGroupBNonDoctoralIntents:
    """Group B intents surface their target SOC at the real education tier.

    Per the SYSTEM_PROMPT rule 3, Gemma must NOT apply doctoral
    preference to these. The candidate pool tests check that:
      1. The Group B SOC actually surfaces (synonym bridging works).
      2. Its education_level reflects the BLS reality (not over-promoted).
    The "doesn't prefer doctoral SOCs" assertion is encoded as: the
    Group B SOC is in the pool with its correct non-doctoral
    education_level, alongside any doctoral decoys that happen to share
    the synonym keyword.
    """

    def test_librarian_intent_surfaces_librarian_soc(self):
        """intent_keywords=['librarian'] → 25-4022 in the candidate pool.
        The synonym map: 'librarian' → 'librar'."""
        pool = _build_candidate_pool(
            ["librarian"],
            base_socs=[],
            cip_family="25",
            query_fn=_make_postgrad_query_fn(),
        )
        assert "25-4022" in pool, (
            f"Librarians SOC 25-4022 must surface for 'librarian' "
            f"intent; got pool {sorted(pool.keys())}"
        )
        # Per BLS: Librarians require a Master's, not a doctoral.
        assert pool["25-4022"]["education_level"] == "Master's degree"

    def test_mortician_intent_does_not_prefer_doctoral_socs(self):
        """Group B negative test: 'mortician' intent surfaces 39-4031
        (Morticians) but does NOT silently promote doctoral SOCs as the
        primary pick.

        The candidate pool surfaces ONLY SOCs whose title/major-group
        contains 'morticia' or 'funeral' (the synonyms). A doctoral SOC
        like 29-1228 (Physicians) doesn't match either keyword, so it
        must NOT be in the pool — this proves the synonym mapping
        doesn't accidentally pull in doctoral decoys."""
        pool = _build_candidate_pool(
            ["mortician"],
            base_socs=[],
            cip_family="12",  # Personal/Culinary Services
            query_fn=_make_postgrad_query_fn(),
        )

        # The Group B SOC surfaces with its real associate's tier.
        assert "39-4031" in pool, (
            f"Morticians SOC 39-4031 must surface; got pool "
            f"{sorted(pool.keys())}"
        )
        assert pool["39-4031"]["education_level"] == "Associate's degree"

        # Doctoral decoys MUST NOT surface — neither 'morticia' nor
        # 'funeral' is in their titles. If a doctoral SOC leaked into
        # the pool here, the doctoral-preference clause might
        # over-promote it past 39-4031 at the Gemma pick stage.
        doctoral_decoys = {"29-1228", "25-1011"}
        leaked = doctoral_decoys & set(pool.keys())
        assert leaked == set(), (
            f"Doctoral SOCs must not appear in the mortician pool — "
            f"would over-promote past the associate's-tier target. "
            f"Leaked: {leaked}"
        )

    def test_music_therapist_intent_does_not_prefer_doctoral_socs(self):
        """Same negative-test pattern for 'music therapist' / 'mt-bc'.

        Music therapy is a bachelor's + certification credential
        (29-1129 → 'Therapists, All Other'). Doctoral decoys must not
        sneak into the candidate pool via the 'therapist' synonym
        without explicit 'music therap' context."""
        pool = _build_candidate_pool(
            ["music therapist"],
            base_socs=[],
            cip_family="50",  # Visual and Performing Arts
            query_fn=_make_postgrad_query_fn(),
        )

        # The Group B SOC surfaces at the bachelor's tier.
        assert "29-1129" in pool, (
            f"'Therapists, All Other' SOC 29-1129 must surface for "
            f"music therapist intent; got pool {sorted(pool.keys())}"
        )
        assert pool["29-1129"]["education_level"] == "Bachelor's degree"

        # Doctoral decoys whose titles don't match 'music therap' or the
        # generic 'therapist' must not leak in. NB: the synonym map for
        # 'music therapist' is ["music therap", "therapist"]; the broad
        # 'therapist' keyword could pull doctoral therapy SOCs if they
        # existed in the pool. The decoys we seeded (29-1228 Physicians,
        # 25-1011 Business Teachers) don't match 'therapist', so they
        # must stay out — confirming Gemma's candidate pool isn't
        # leaking doctoral roles unrelated to music therapy.
        doctoral_decoys = {"29-1228", "25-1011"}
        leaked = doctoral_decoys & set(pool.keys())
        assert leaked == set(), (
            f"Unrelated doctoral SOCs must not appear in the music "
            f"therapist pool. Leaked: {leaked}"
        )
