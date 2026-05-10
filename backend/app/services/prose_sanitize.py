"""Markdown / formatting strippers for Gemma prose surfaces.

Defense-in-depth utility: the streaming-intent prompt (and several other
prompts) ask Gemma for plain prose, but smaller local models (e.g.
gemma4:e4b on Ollama) habitually emit markdown formatting, numeric
codes, and unsolicited disclaimers. Frontend surfaces other than Ask
Gemma render plain text via ``whitespace-pre-wrap`` / ``-pre-line``,
so unstripped markdown shows up literally as ``**bold**`` etc.

Two entry points:
    * ``strip_markdown`` — non-streaming. Run on a complete string
      before returning it to the frontend or persisting it.
    * ``strip_markdown_streaming`` — streaming-safe. Caller maintains
      the assembled buffer and an emitted-length cursor; this returns
      the cleanly-stripped prefix that's safe to flush given a holdback
      window for unfinished markers.

A third helper, ``strip_inline_markdown_preserving_h2``, is for the
``next_steps`` surface where ``## Section`` headers are part of the
contract that the frontend parser depends on; only inline markdown
inside section bodies is stripped.

Idempotent: ``strip_markdown(strip_markdown(x)) == strip_markdown(x)``.
"""

from __future__ import annotations

import re

# Numeric codes like 52.1401 (CIP), 11-1011 (SOC), 12.34, etc., emitted
# in parentheses inline. Reused from the older inline-cleaner that lived
# in set_your_course.py.
_NUMERIC_CODE_PARENTHETICAL = re.compile(r"\s*\(\s*\d{2}[.\-]\d{2,4}\s*\)")

# Standalone numeric code occurrences in prose: 52.1401, 52.14.21, 11-1011.
# We strip these because (a) the streaming intent prompt forbids them
# and (b) Gemma sometimes hallucinates malformed codes (e.g. 52.14.21).
_INLINE_NUMERIC_CODE = re.compile(r"\b\d{2}[.\-]\d{2,4}(?:[.\-]\d{1,4})?\b")

# Triple-backtick fence with optional language tag.
_TRIPLE_BACKTICK_FENCE = re.compile(r"```[a-zA-Z0-9_+\-]*\n?|```")

# Bold ``**text**`` and ``__text__``. Non-greedy, single-line.
_BOLD_DOUBLE_STAR = re.compile(r"\*\*([^*\n][^*\n]*?)\*\*")
_BOLD_DOUBLE_UNDER = re.compile(r"__([^_\n][^_\n]*?)__")

# Italic ``*text*`` and ``_text_``. We require non-space adjacency so we
# don't accidentally consume legitimate asterisks in math/footnote text.
_ITALIC_SINGLE_STAR = re.compile(r"(?<![*\w])\*(?!\s)([^*\n]+?)(?<!\s)\*(?!\w)")
_ITALIC_SINGLE_UNDER = re.compile(r"(?<![_\w])_(?!\s)([^_\n]+?)(?<!\s)_(?!\w)")

# Inline code ``` `text` ```.
_INLINE_CODE = re.compile(r"`([^`\n]+?)`")

# Leading ATX header markers (``#``, ``##``, ``###``...). Strip the marker
# and surrounding space; keep the heading text.
_HEADER_LINE = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+", flags=re.MULTILINE)

# Leading bullet markers: ``-``, ``*``, ``+``, or ``•`` followed by
# whitespace. Drop the marker; keep the item text on the same line.
_BULLET_LINE = re.compile(
    r"^[ \t]*(?:[-*+•]|\d+[.)])[ \t]+",
    flags=re.MULTILINE,
)

# Horizontal rule lines: ``---``, ``***``, ``___`` alone on a line
# (optionally surrounded by whitespace). Drop the whole line.
_HORIZONTAL_RULE_LINE = re.compile(
    r"^[ \t]*(?:-{3,}|\*{3,}|_{3,})[ \t]*$\n?",
    flags=re.MULTILINE,
)

# Three or more consecutive newlines collapse to a paragraph break.
_RUN_OF_NEWLINES = re.compile(r"\n{3,}")

# Stray emphasis-marker characters left after balanced patterns have
# matched. Match runs of 1+ so streaming-time stripping of an unfinished
# ``**bold`` (no closer yet) produces the same content as full-text
# stripping of the eventual ``**bold**`` — a property the streaming
# state machine in set_your_course.py relies on for monotonic emits.
# Sweeping single ``*``/``_``/`` ` `` is safe across our prose surfaces:
# none legitimately contain math notation, snake_case identifiers, or
# inline-code spans.
_TRAILING_ASTERISK_RUN = re.compile(r"\*+")
_TRAILING_UNDERSCORE_RUN = re.compile(r"_+")
_STRAY_BACKTICK = re.compile(r"`+")


def strip_markdown(text: str) -> str:
    """Remove markdown formatting from prose while preserving content.

    Order matters: fences and HRs go first, then headers/bullets at
    line starts, then inline emphasis, then leftover marker runs, then
    numeric codes, then whitespace normalization.
    """
    if not text:
        return text

    out = text

    # Triple-backtick fences: drop the fences, keep the contents.
    out = _TRIPLE_BACKTICK_FENCE.sub("", out)

    # Horizontal rules on their own lines.
    out = _HORIZONTAL_RULE_LINE.sub("", out)

    # Leading header markers and bullets.
    out = _HEADER_LINE.sub("", out)
    out = _BULLET_LINE.sub("", out)

    # Inline emphasis. Apply repeatedly to handle nested cases like
    # ``**_bold-italic_**`` until the string stabilizes.
    prev = ""
    iterations = 0
    while prev != out and iterations < 4:
        prev = out
        out = _BOLD_DOUBLE_STAR.sub(r"\1", out)
        out = _BOLD_DOUBLE_UNDER.sub(r"\1", out)
        out = _ITALIC_SINGLE_STAR.sub(r"\1", out)
        out = _ITALIC_SINGLE_UNDER.sub(r"\1", out)
        out = _INLINE_CODE.sub(r"\1", out)
        iterations += 1

    # Sweep stray marker runs that survived (unbalanced ``**``, single
    # ``*``, stray backticks, etc.). Critical for streaming: a partial
    # ``**bold`` (no closer yet) must clean to the same content as the
    # eventual ``**bold**`` so the cumulative-emit diff is monotonic.
    out = _TRAILING_ASTERISK_RUN.sub("", out)
    out = _TRAILING_UNDERSCORE_RUN.sub("", out)
    out = _STRAY_BACKTICK.sub("", out)

    # Numeric-code parentheticals first (so the inline pass below
    # doesn't have to mop up their parentheses).
    out = _NUMERIC_CODE_PARENTHETICAL.sub("", out)
    out = _INLINE_NUMERIC_CODE.sub("", out)

    # Tidy: collapse runs of newlines, trim trailing spaces per line,
    # trim outer whitespace.
    out = _RUN_OF_NEWLINES.sub("\n\n", out)
    out = "\n".join(line.rstrip() for line in out.split("\n"))
    return out.strip()


def strip_markdown_streaming(
    buffer: str,
    holdback: int,
) -> tuple[str, int]:
    """Streaming-safe markdown stripper.

    Args:
        buffer: The full assembled raw-prose buffer received so far.
        holdback: Number of trailing characters to keep buffered
            because they might be part of an unfinished marker
            (e.g. a chunk ending in ``"*"`` could be the start of
            ``"**bold**"``). Callers typically already hold back
            for the JSON delimiter; pass that same holdback here.

    Returns:
        A tuple ``(clean_prefix, consumed_len)`` where:
            * ``clean_prefix`` is the markdown-stripped version of
              ``buffer[:consumed_len]``.
            * ``consumed_len`` is the number of raw-buffer chars that
              were processed (i.e. ``len(buffer) - holdback``,
              floored at 0).

        The caller subtracts the previously-emitted clean length to
        get the new bytes to flush.
    """
    if not buffer:
        return "", 0

    consumed_len = max(0, len(buffer) - holdback)
    if consumed_len == 0:
        return "", 0

    safe_prefix = buffer[:consumed_len]
    return _strip_markdown_monotonic(safe_prefix), consumed_len


def _strip_markdown_monotonic(text: str) -> str:
    """Monotonic markdown strip for in-stream emit.

    Critically does NOT strip numeric codes, horizontal rules, or
    triple-backtick fences. Those operations are non-monotonic
    against streaming chunks — e.g. a partial buffer ``"**52.1"`` and
    its eventual extension ``"**52.1421 Marketing**"`` produce
    different cleaned content (``"52.1"`` vs. ``"Marketing"``), and
    ``"52.1"`` is not a prefix of ``"Marketing"``. If we emit ``52.1``
    early and then later try to emit the diff against ``Marketing``,
    the user sees corrupted gibberish (``"52rketing"`` was the
    observed symptom in the e4b stream).

    The full ``strip_markdown`` runs at end-of-stream so the final
    cleaned reasoning is correct; this monotonic variant is the
    safe-to-emit subset.
    """
    if not text:
        return text
    out = text
    # Only line-leading block markers (header, bullet) and balanced
    # inline emphasis are stripped here — the operations whose result
    # only adds-to-the-prefix as more buffer arrives.
    out = _HEADER_LINE.sub("", out)
    out = _BULLET_LINE.sub("", out)
    prev = ""
    iterations = 0
    while prev != out and iterations < 4:
        prev = out
        out = _BOLD_DOUBLE_STAR.sub(r"\1", out)
        out = _BOLD_DOUBLE_UNDER.sub(r"\1", out)
        out = _ITALIC_SINGLE_STAR.sub(r"\1", out)
        out = _ITALIC_SINGLE_UNDER.sub(r"\1", out)
        out = _INLINE_CODE.sub(r"\1", out)
        iterations += 1
    out = _TRAILING_ASTERISK_RUN.sub("", out)
    out = _TRAILING_UNDERSCORE_RUN.sub("", out)
    out = _STRAY_BACKTICK.sub("", out)
    out = _RUN_OF_NEWLINES.sub("\n\n", out)
    out = "\n".join(line.rstrip() for line in out.split("\n"))
    return out.strip()


# --------------------------------------------------------------------------
# next_steps surface — preserve ``## Section`` markers, strip the rest.
# --------------------------------------------------------------------------


_H2_LINE = re.compile(r"^[ \t]{0,3}##[ \t]+", flags=re.MULTILINE)


_NUMBERED_LIST_MARKER = re.compile(
    r"^[ \t]*\d+[.)][ \t]+",
    flags=re.MULTILINE,
)


def strip_inline_markdown_preserving_h2(text: str) -> str:
    """Strip inline markdown but keep ``## Section`` H2 headers and
    numbered-list markers intact.

    The Next Steps frontend parser splits on ``## `` headers to break
    the response into sections, and the prompt contract asks for
    numbered items (``1. ...``) within each section. Stripping either
    would corrupt rendering. So inside section bodies we run a
    targeted inline cleanup (bold/italic/inline-code/horizontal-rule
    /numeric-code stripping) but leave the H2 markers and numbered
    bullets in place.
    """
    if not text:
        return text

    # Split into segments around H2 markers, preserving them as
    # captured groups.
    parts = re.split(r"(?m)(^[ \t]{0,3}##[ \t]+[^\n]*$)", text)
    cleaned_parts: list[str] = []
    for part in parts:
        if _H2_LINE.match(part):
            cleaned_parts.append(part.rstrip())
        else:
            cleaned_parts.append(_strip_inline_only(part))

    joined = "\n".join(p for p in cleaned_parts if p)
    return _RUN_OF_NEWLINES.sub("\n\n", joined).strip()


def _strip_inline_only(text: str) -> str:
    """Strip emphasis, inline code, fences, HRs, and numeric codes,
    but keep numbered-list and bullet markers (next_steps content)."""
    if not text:
        return text
    out = text
    out = _TRIPLE_BACKTICK_FENCE.sub("", out)
    out = _HORIZONTAL_RULE_LINE.sub("", out)
    # No header strip and no bullet strip here.
    prev = ""
    iterations = 0
    while prev != out and iterations < 4:
        prev = out
        out = _BOLD_DOUBLE_STAR.sub(r"\1", out)
        out = _BOLD_DOUBLE_UNDER.sub(r"\1", out)
        out = _ITALIC_SINGLE_STAR.sub(r"\1", out)
        out = _ITALIC_SINGLE_UNDER.sub(r"\1", out)
        out = _INLINE_CODE.sub(r"\1", out)
        iterations += 1
    out = _TRAILING_ASTERISK_RUN.sub("", out)
    out = _TRAILING_UNDERSCORE_RUN.sub("", out)
    out = _STRAY_BACKTICK.sub("", out)
    out = _NUMERIC_CODE_PARENTHETICAL.sub("", out)
    out = _INLINE_NUMERIC_CODE.sub("", out)
    out = _RUN_OF_NEWLINES.sub("\n\n", out)
    out = "\n".join(line.rstrip() for line in out.split("\n"))
    return out.strip()
