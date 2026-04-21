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
