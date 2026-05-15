"""Tests for ``app.services.prose_sanitize``.

Coverage targets:
    * Inline markdown: bold, italic, inline code (in both ``*`` and
      ``_`` flavors), with the user-reported buggy output as a fixture.
    * Block markdown: headers, bullets, fences, horizontal rules.
    * Numeric-code stripping: well-formed CIPs in parens, malformed
      hallucinations like ``52.14.21``.
    * Whitespace normalization (3+ newlines collapse to 2).
    * Idempotency: running twice equals running once.
    * Streaming variant: holdback prevents partial-marker emission;
      cumulative emits over multiple chunks reconstruct the same
      output as a single non-streaming call.
    * H2-preserving variant: ``## Section`` markers survive while
      inline formatting inside the body is stripped.
"""

from __future__ import annotations

import pytest

from app.services.prose_sanitize import (
    strip_markdown,
    strip_markdown_streaming,
)

# --------------------------------------------------------------------------
# strip_markdown — inline emphasis
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("**bold**", "bold"),
        ("*italic*", "italic"),
        ("__bold__", "bold"),
        ("_italic_", "italic"),
        ("`inline code`", "inline code"),
        ("plain text", "plain text"),
        ("", ""),
        ("a **b** c", "a b c"),
        ("**Recommended Program:** Marketing", "Recommended Program: Marketing"),
        # Nested: ** wraps _italic_.
        ("**_bold italic_**", "bold italic"),
    ],
)
def test_strip_markdown_inline(raw: str, expected: str) -> None:
    assert strip_markdown(raw) == expected


def test_strip_markdown_unbalanced_markers_are_swept() -> None:
    """A stray ``**`` left after the matched-pass should be removed."""
    assert "**" not in strip_markdown("hello ** world")
    assert "***" not in strip_markdown("***")


# --------------------------------------------------------------------------
# strip_markdown — block elements
# --------------------------------------------------------------------------


def test_strip_markdown_headers() -> None:
    assert strip_markdown("# Title\nbody") == "Title\nbody"
    assert strip_markdown("## Section\nbody") == "Section\nbody"
    assert strip_markdown("### Sub\nbody") == "Sub\nbody"


def test_strip_markdown_bullets() -> None:
    raw = "- item one\n- item two\n* item three\n+ item four"
    assert strip_markdown(raw) == "item one\nitem two\nitem three\nitem four"


def test_strip_markdown_numbered_list() -> None:
    raw = "1. first\n2. second"
    assert strip_markdown(raw) == "first\nsecond"


def test_strip_markdown_triple_backtick_fence() -> None:
    raw = "```json\n{\"a\": 1}\n```"
    assert strip_markdown(raw) == '{"a": 1}'


def test_strip_markdown_horizontal_rule() -> None:
    raw = "Above\n\n---\n\nBelow"
    assert "---" not in strip_markdown(raw)


# --------------------------------------------------------------------------
# strip_markdown — numeric codes
# --------------------------------------------------------------------------


def test_strip_markdown_parenthetical_cip() -> None:
    raw = "Marketing (52.1401) is a fit."
    out = strip_markdown(raw)
    assert "52.1401" not in out
    assert "(" not in out
    assert "Marketing" in out


def test_strip_markdown_inline_cip_codes() -> None:
    raw = "The code 52.1401 maps to Marketing."
    assert "52.1401" not in strip_markdown(raw)


def test_strip_markdown_hallucinated_malformed_code() -> None:
    """Three-segment numeric like ``52.14.21`` (the bug we observed)."""
    raw = "**52.14.21 Marketing:** this is the program."
    out = strip_markdown(raw)
    assert "52.14.21" not in out
    assert "**" not in out
    assert "Marketing" in out


# --------------------------------------------------------------------------
# strip_markdown — full bug fixture
# --------------------------------------------------------------------------


def test_strip_markdown_full_observed_bug_fixture() -> None:
    """The exact symptom from the user report: markdown + fake codes
    + horizontal rule + disclaimer block. After stripping, no asterisks,
    no triple-dash, no malformed code."""
    raw = (
        "Based on your interest in \"Marketing,\" here are the most "
        "relevant program options:\n\n"
        "**Recommended Program:**\n"
        "*   **52.14.21 Marketing:** This is a general degree.\n\n"
        "**Other Potential Areas of Interest:**\n"
        "*   **52.14.22 Advertising:** If your interest leans more...\n"
        "*   **52.14.23 Public Relations:** If you are interested...\n\n"
        "***\n\n"
        "**Disclaimer:** I am an AI assistant and cannot provide..."
    )
    out = strip_markdown(raw)
    assert "**" not in out
    assert "***" not in out
    assert "52.14.21" not in out
    assert "52.14.22" not in out
    assert "52.14.23" not in out
    assert "Marketing" in out
    assert "Disclaimer:" in out  # content kept; only formatting stripped


# --------------------------------------------------------------------------
# strip_markdown — whitespace + idempotency
# --------------------------------------------------------------------------


def test_strip_markdown_collapses_long_newline_runs() -> None:
    raw = "a\n\n\n\n\nb"
    assert strip_markdown(raw) == "a\n\nb"


def test_strip_markdown_idempotent() -> None:
    fixtures = [
        "**bold** and *italic* and ` code `",
        "## Header\n\n- bullet\n- bullet\n\n```\nfence\n```",
        "Marketing (52.1401) is great.",
        "***",
    ]
    for raw in fixtures:
        once = strip_markdown(raw)
        twice = strip_markdown(once)
        assert once == twice, f"not idempotent for: {raw!r}"


# --------------------------------------------------------------------------
# strip_markdown_streaming — holdback semantics
# --------------------------------------------------------------------------


def test_streaming_holdback_prevents_partial_marker() -> None:
    """A buffer ending in ``*`` could be the start of ``**``; with a
    holdback >= 2 the trailing ``*`` is held back rather than emitted
    as a literal."""
    clean, consumed = strip_markdown_streaming("Marketing *", holdback=2)
    assert "*" not in clean
    assert consumed == len("Marketing *") - 2


def test_streaming_zero_consumed_when_buffer_smaller_than_holdback() -> None:
    clean, consumed = strip_markdown_streaming("ab", holdback=10)
    assert clean == ""
    assert consumed == 0


def test_streaming_emits_whole_buffer_at_end_with_zero_holdback() -> None:
    raw = "Marketing **is** a good fit."
    clean, consumed = strip_markdown_streaming(raw, holdback=0)
    assert consumed == len(raw)
    assert "**" not in clean
    assert "Marketing is a good fit." == clean


def test_streaming_is_monotonic_across_partial_bold_with_numeric_code() -> None:
    """The exact failure mode from the e4b stream that produced
    ``52arketing``: bold-wrapped numeric code arriving in chunks. The
    streaming sanitizer must NEVER emit a clean prefix that becomes
    a non-prefix of the cleaned full text — once the closing ``**``
    arrives, the diff against what we already emitted has to be a
    pure suffix to append."""
    chunks_in_order = [
        "**52",
        ".1421 ",
        "Marketing**",
        " is a general program.",
    ]
    holdback = 16
    assembled = ""
    last_clean_len = 0
    cumulative_emit = ""
    for chunk in chunks_in_order:
        assembled += chunk
        clean, _ = strip_markdown_streaming(assembled, holdback)
        # Monotonicity: every clean prefix must extend the previous one.
        assert clean.startswith(cumulative_emit), (
            f"non-monotonic emit: previous {cumulative_emit!r} is not a "
            f"prefix of new {clean!r}"
        )
        new_part = clean[last_clean_len:]
        cumulative_emit += new_part
        last_clean_len = len(clean)

    # Final flush at end-of-stream (holdback=0).
    final, _ = strip_markdown_streaming(assembled, holdback=0)
    assert final.startswith(cumulative_emit), (
        f"end-of-stream flush violated monotonicity: {cumulative_emit!r} "
        f"vs {final!r}"
    )
    # Most importantly, the user-visible text contains no corruption.
    assert "52arketing" not in cumulative_emit
    assert "52rketing" not in cumulative_emit
    assert "Marketing" in cumulative_emit


def test_streaming_cumulative_matches_nonstreaming() -> None:
    """Simulate chunked arrival; cumulative clean output should equal
    the single-shot ``strip_markdown`` result once the stream ends."""
    chunks = ["Marke", "ting **", "is** a good ", "fit."]
    holdback = 3  # > len("**") - 1, so partial markers stay buffered
    assembled = ""
    last_clean_len = 0
    streamed: list[str] = []
    for c in chunks:
        assembled += c
        clean, _consumed = strip_markdown_streaming(assembled, holdback)
        new_part = clean[last_clean_len:]
        if new_part:
            streamed.append(new_part)
        last_clean_len = len(clean)
    # Final flush with holdback=0.
    final_clean, _ = strip_markdown_streaming(assembled, holdback=0)
    new_tail = final_clean[last_clean_len:]
    if new_tail:
        streamed.append(new_tail)

    streamed_full = "".join(streamed)
    one_shot = strip_markdown(assembled)
    assert streamed_full == one_shot
    assert "**" not in streamed_full


