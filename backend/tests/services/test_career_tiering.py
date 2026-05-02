"""Tests for Gemma-driven career tiering."""

from __future__ import annotations

from app.models.career import BossScores, CareerOutcome, PentagonStats
from app.services import career_tiering


def _outcome(soc: str, title: str = "Test", wage: float = 50000.0) -> CareerOutcome:
    return CareerOutcome(
        unitid=1,
        institution_name="Test U",
        cipcode="52.14",
        program_name="Marketing",
        soc_code=soc,
        occupation_title=title,
        stats=PentagonStats(ern=5, roi=5, res=5, grw=5, aura=5),
        bosses=BossScores(ai=5, loans=5, market=5, burnout=5, ceiling=5),
        median_annual_wage=wage,
        stats_available_count=5,
        overall_confidence="high",
        education_level_name="Bachelor's degree",
    )


def _outcomes_8() -> list[CareerOutcome]:
    return [
        _outcome("11-2021", "Marketing Managers", 161030),
        _outcome("13-1161", "Market Research Analysts", 76950),
        _outcome("11-2022", "Sales Managers", 138060),
        _outcome("13-1131", "Fundraisers", 66490),
        _outcome("11-2011", "Advertising Managers", 123480),
        _outcome("27-3031", "Public Relations Specialists", 67440),
        _outcome("11-3011", "Administrative Services Managers", 112890),
        _outcome("13-1199", "Business Operations Specialists", 82060),
    ]


class TestParseTiers:
    def test_parses_well_formed_output(self):
        text = (
            "COMMON\n"
            "11-2021\n"
            "13-1161\n"
            "11-2022\n"
            "LESS_COMMON\n"
            "13-1131\n"
            "11-2011\n"
            "27-3031\n"
            "STRETCH\n"
            "11-3011\n"
            "13-1199\n"
        )
        outcomes = _outcomes_8()
        lookup = {o.soc_code: o for o in outcomes}
        tiers = career_tiering._parse_tiers(text, lookup)
        common = tiers[career_tiering.TIER_COMMON]
        less_common = tiers[career_tiering.TIER_LESS_COMMON]
        stretch = tiers[career_tiering.TIER_STRETCH]
        assert len(common) == 3
        assert len(less_common) == 3
        assert len(stretch) == 2
        assert common[0].soc_code == "11-2021"

    def test_handles_extra_text_around_soc(self):
        text = (
            "COMMON\n"
            "11-2021 Marketing Managers\n"
            "13-1161 (most common analytical path)\n"
            "LESS_COMMON\n"
            "11-2022\n"
            "STRETCH\n"
            "13-1131\n"
        )
        outcomes = _outcomes_8()
        lookup = {o.soc_code: o for o in outcomes}
        tiers = career_tiering._parse_tiers(text, lookup)
        assert len(tiers[career_tiering.TIER_COMMON]) == 2
        assert len(tiers[career_tiering.TIER_LESS_COMMON]) == 1
        # Unplaced outcomes land in STRETCH via catch-all.
        assert len(tiers[career_tiering.TIER_STRETCH]) >= 1

    def test_unplaced_socs_land_in_stretch(self):
        text = (
            "COMMON\n"
            "11-2021\n"
            "LESS_COMMON\n"
            "13-1161\n"
            "STRETCH\n"
        )
        outcomes = _outcomes_8()
        lookup = {o.soc_code: o for o in outcomes}
        tiers = career_tiering._parse_tiers(text, lookup)
        placed = (
            len(tiers[career_tiering.TIER_COMMON])
            + len(tiers[career_tiering.TIER_LESS_COMMON])
        )
        assert placed == 2
        assert len(tiers[career_tiering.TIER_STRETCH]) == 6

    def test_unknown_soc_codes_silently_dropped(self):
        text = "COMMON\n99-9999\nLESS_COMMON\nSTRETCH\n"
        outcomes = _outcomes_8()
        lookup = {o.soc_code: o for o in outcomes}
        tiers = career_tiering._parse_tiers(text, lookup)
        assert len(tiers[career_tiering.TIER_COMMON]) == 0

    def test_duplicate_soc_placed_once(self):
        text = (
            "COMMON\n"
            "11-2021\n"
            "11-2021\n"
            "LESS_COMMON\n"
            "11-2021\n"
            "STRETCH\n"
        )
        lookup = {"11-2021": _outcome("11-2021")}
        tiers = career_tiering._parse_tiers(text, lookup)
        total = sum(len(v) for v in tiers.values())
        assert total == 1


class TestTierCareers:
    def test_small_list_skips_gemma(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            career_tiering.gemma_client,
            "generate",
            lambda **kw: (calls.append(1), "")[1],
        )
        outcomes = _outcomes_8()[:3]
        tiers = career_tiering.tier_careers(
            outcomes, "Test U", "Marketing", "52.14"
        )
        assert calls == []
        assert "All career paths" in tiers
        assert len(tiers["All career paths"]) == 3

    def test_uses_gemma_when_enough_outcomes(self, monkeypatch):
        fake = (
            "COMMON\n11-2021\n13-1161\n11-2022\n"
            "LESS_COMMON\n13-1131\n11-2011\n27-3031\n"
            "STRETCH\n11-3011\n13-1199\n"
        )
        monkeypatch.setattr(
            career_tiering.gemma_client, "generate", lambda **kw: fake
        )
        tiers = career_tiering.tier_careers(
            _outcomes_8(), "Test U", "Marketing", "52.14"
        )
        assert career_tiering.TIER_COMMON in tiers
        assert career_tiering.TIER_LESS_COMMON in tiers
        assert career_tiering.TIER_STRETCH in tiers
        assert len(tiers[career_tiering.TIER_COMMON]) == 3

    def test_gemma_failure_falls_back(self, monkeypatch):
        monkeypatch.setattr(
            career_tiering.gemma_client, "generate", lambda **kw: ""
        )
        tiers = career_tiering.tier_careers(
            _outcomes_8(), "Test U", "Marketing", "52.14"
        )
        assert "All career paths" in tiers
        assert len(tiers["All career paths"]) == 8

    def test_prompt_includes_school_and_all_socs(self, monkeypatch):
        captured: dict = {}

        def capture(**kw):
            captured.update(kw)
            return ""

        monkeypatch.setattr(career_tiering.gemma_client, "generate", capture)
        outcomes = _outcomes_8()
        career_tiering.tier_careers(outcomes, "IU-B", "Marketing", "52.14")
        user = captured["user"]
        assert "IU-B" in user
        assert "Marketing" in user
        assert "52.14" in user
        for outcome in outcomes:
            assert outcome.soc_code in user

    def test_empty_tiers_pruned(self, monkeypatch):
        fake = (
            "COMMON\n11-2021\n13-1161\n11-2022\n13-1131\n"
            "11-2011\n27-3031\n11-3011\n13-1199\n"
            "LESS_COMMON\n"
            "STRETCH\n"
        )
        monkeypatch.setattr(
            career_tiering.gemma_client, "generate", lambda **kw: fake
        )
        tiers = career_tiering.tier_careers(
            _outcomes_8(), "Test U", "Marketing", "52.14"
        )
        assert career_tiering.TIER_LESS_COMMON not in tiers
        assert career_tiering.TIER_STRETCH not in tiers
        assert len(tiers[career_tiering.TIER_COMMON]) == 8


# ---------------------------------------------------------------------------
# Intent-aware tiering prompt tests (P0)
# ---------------------------------------------------------------------------


class TestIntentAwarePrompt:
    """Verify that ``_prompt`` and ``tier_careers`` correctly inject (or
    omit) the STUDENT INTENT block and INTENT MATCH RULES based on the
    ``student_major_text`` and ``intent_keywords`` arguments."""

    def test_no_intent_preserves_existing_behavior(self, monkeypatch):
        """When both intent_keywords and student_major_text are empty/absent,
        the prompt must NOT contain the STUDENT INTENT block or INTENT MATCH
        RULES — and the Gemma call + parse pipeline is identical to the
        pre-intent codepath."""
        captured: dict = {}

        def capture(**kw):
            captured.update(kw)
            return (
                "COMMON\n11-2021\n13-1161\n11-2022\n"
                "LESS_COMMON\n13-1131\n11-2011\n27-3031\n"
                "STRETCH\n11-3011\n13-1199\n"
            )

        monkeypatch.setattr(career_tiering.gemma_client, "generate", capture)
        outcomes = _outcomes_8()

        # Call WITHOUT intent args (backwards compat)
        tiers_no_args = career_tiering.tier_careers(
            outcomes, "Test U", "Marketing", "52.14"
        )
        prompt_no_args = captured["user"]

        assert "STUDENT INTENT" not in prompt_no_args
        assert "INTENT MATCH RULES" not in prompt_no_args

        # Call WITH explicitly empty intent args
        career_tiering.tier_careers(
            outcomes,
            "Test U",
            "Marketing",
            "52.14",
            student_major_text="",
            intent_keywords=[],
        )
        prompt_empty = captured["user"]
        assert "STUDENT INTENT" not in prompt_empty
        assert "INTENT MATCH RULES" not in prompt_empty

        # Also verify None for intent_keywords
        career_tiering.tier_careers(
            outcomes,
            "Test U",
            "Marketing",
            "52.14",
            student_major_text="",
            intent_keywords=None,
        )
        prompt_none = captured["user"]
        assert "STUDENT INTENT" not in prompt_none
        assert "INTENT MATCH RULES" not in prompt_none

        # Tiers still parse correctly (basic sanity)
        assert career_tiering.TIER_COMMON in tiers_no_args
        assert len(tiers_no_args[career_tiering.TIER_COMMON]) == 3

    def test_intent_keywords_inject_student_intent_block(self, monkeypatch):
        """When intent_keywords are provided, the prompt must contain
        STUDENT INTENT and INTENT MATCH RULES sections."""
        captured: dict = {}

        def capture(**kw):
            captured.update(kw)
            return (
                "COMMON\n11-2021\n13-1161\n11-2022\n"
                "LESS_COMMON\n13-1131\n11-2011\n27-3031\n"
                "STRETCH\n11-3011\n13-1199\n"
            )

        monkeypatch.setattr(career_tiering.gemma_client, "generate", capture)

        career_tiering.tier_careers(
            _outcomes_8(),
            "IU-B",
            "Biology",
            "26.0101",
            student_major_text="biology pre-med",
            intent_keywords=["pre-med", "doctor", "physician"],
        )
        prompt = captured["user"]

        assert "STUDENT INTENT" in prompt
        assert 'The student typed: "biology pre-med"' in prompt
        assert "pre-med, doctor, physician" in prompt
        assert "INTENT MATCH RULES" in prompt
        # The rules mention demotion logic for education mismatch
        assert "demote" in prompt.lower()
        # The rules mention promotion for direct matches
        assert "promote" in prompt.lower()

    def test_student_major_text_alone_triggers_intent_block(self, monkeypatch):
        """Even without intent_keywords, providing student_major_text
        alone should inject the STUDENT INTENT block (the text itself is
        signal to Gemma)."""
        captured: dict = {}

        def capture(**kw):
            captured.update(kw)
            return ""

        monkeypatch.setattr(career_tiering.gemma_client, "generate", capture)

        career_tiering.tier_careers(
            _outcomes_8(),
            "Test U",
            "Special Education",
            "13.1001",
            student_major_text="deaf education",
            intent_keywords=[],
        )
        prompt = captured["user"]

        assert "STUDENT INTENT" in prompt
        assert 'The student typed: "deaf education"' in prompt
        assert "INTENT MATCH RULES" in prompt

    def test_intent_keywords_alone_triggers_intent_block(self, monkeypatch):
        """Intent keywords without student_major_text still injects the
        block (keywords are the primary signal)."""
        captured: dict = {}

        def capture(**kw):
            captured.update(kw)
            return ""

        monkeypatch.setattr(career_tiering.gemma_client, "generate", capture)

        career_tiering.tier_careers(
            _outcomes_8(),
            "Test U",
            "Special Education",
            "13.1001",
            student_major_text="",
            intent_keywords=["deaf education", "special education"],
        )
        prompt = captured["user"]

        assert "STUDENT INTENT" in prompt
        assert "deaf education, special education" in prompt
        assert "INTENT MATCH RULES" in prompt
        # No student-typed line since student_major_text is empty
        assert 'The student typed:' not in prompt

    def test_prompt_directly_with_and_without_intent(self):
        """Test the ``_prompt`` function directly as a pure function
        to verify intent block injection without any mocking overhead."""
        outcomes = _outcomes_8()

        # Without intent
        prompt_no_intent = career_tiering._prompt(
            outcomes, "Test U", "Marketing", "52.14"
        )
        assert "STUDENT INTENT" not in prompt_no_intent
        assert "INTENT MATCH RULES" not in prompt_no_intent

        # With intent
        prompt_with_intent = career_tiering._prompt(
            outcomes,
            "Test U",
            "Marketing",
            "52.14",
            student_major_text="marketing analytics",
            intent_keywords=["analytics", "data"],
        )
        assert "STUDENT INTENT" in prompt_with_intent
        assert 'The student typed: "marketing analytics"' in prompt_with_intent
        assert "analytics, data" in prompt_with_intent
        assert "INTENT MATCH RULES" in prompt_with_intent

    def test_intent_keywords_for_special_ed_case(self, monkeypatch):
        """The deaf-ed case from the spec: verify the prompt carries
        intent keywords that would let Gemma demote program-negating
        titles (e.g., generic admin roles for a deaf-ed student)."""
        captured: dict = {}

        def capture(**kw):
            captured.update(kw)
            return (
                "COMMON\n11-2021\n13-1161\n11-2022\n"
                "LESS_COMMON\n13-1131\n11-2011\n27-3031\n"
                "STRETCH\n11-3011\n13-1199\n"
            )

        monkeypatch.setattr(career_tiering.gemma_client, "generate", capture)

        career_tiering.tier_careers(
            _outcomes_8(),
            "Indiana University",
            "Special Education and Teaching",
            "13.1001",
            student_major_text="deaf ed",
            intent_keywords=["deaf education", "special education", "teacher"],
        )
        prompt = captured["user"]

        assert "STUDENT INTENT" in prompt
        assert 'The student typed: "deaf ed"' in prompt
        assert "deaf education" in prompt
        assert "teacher" in prompt
        assert "INTENT MATCH RULES" in prompt
