"""Render the 6 Wrapped story frames as 1080×1920 PNGs via Playwright.

Orchestration:
1. For each frame: render Jinja2 HTML template with build data.
2. Launch headless Chromium once.
3. Set viewport to 1080×1920.
4. For each rendered HTML: set_content → wait for fonts → screenshot.
5. Close browser, return list of (index, png_bytes) tuples.

The renderer is stateless and async. The caller (wrapped router) is
responsible for persisting the bytes to DuckDB and caching.

Playwright is a hard dependency — if it's not installed, the import
fails and the endpoint returns 500. Per spec §2 this is an accepted
hackathon trade-off.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jinja2 import (  # type: ignore[import-not-found]
    Environment,
    FileSystemLoader,
    select_autoescape,
)

from app.models.career import Build
from app.services.mcp_client import project_root

logger = logging.getLogger(__name__)


_BOSS_EMOJI: dict[str, str] = {
    "ai": "🧠",
    "loans": "💰",
    "market": "📈",
    "burnout": "💜",
    "ceiling": "⬆️",
}

_BOSS_COLORS: dict[str, dict[str, str]] = {
    "ai": {
        "base": "#B8A9E8",
        "strong": "rgba(184, 169, 232, 0.45)",
        "halo": "rgba(184, 169, 232, 0.22)",
        "shadow": "rgba(184, 169, 232, 0.5)",
    },
    "loans": {
        "base": "#F4A97E",
        "strong": "rgba(244, 169, 126, 0.45)",
        "halo": "rgba(244, 169, 126, 0.22)",
        "shadow": "rgba(244, 169, 126, 0.5)",
    },
    "market": {
        "base": "#7BB8E0",
        "strong": "rgba(123, 184, 224, 0.45)",
        "halo": "rgba(123, 184, 224, 0.22)",
        "shadow": "rgba(123, 184, 224, 0.5)",
    },
    "burnout": {
        "base": "#E88BA9",
        "strong": "rgba(232, 139, 169, 0.45)",
        "halo": "rgba(232, 139, 169, 0.22)",
        "shadow": "rgba(232, 139, 169, 0.5)",
    },
    "ceiling": {
        "base": "#C4BFB0",
        "strong": "rgba(196, 191, 176, 0.45)",
        "halo": "rgba(196, 191, 176, 0.22)",
        "shadow": "rgba(196, 191, 176, 0.5)",
    },
}

_STAT_COLORS: dict[str, dict[str, str]] = {
    "ern": {"base": "#F2D477", "halo": "rgba(242, 212, 119, 0.35)"},
    "roi": {"base": "#7DD4A3", "halo": "rgba(125, 212, 163, 0.35)"},
    "res": {"base": "#B8A9E8", "halo": "rgba(184, 169, 232, 0.35)"},
    "grw": {"base": "#7BB8E0", "halo": "rgba(123, 184, 224, 0.35)"},
    "aura": {"base": "#E8B86B", "halo": "rgba(232, 184, 107, 0.35)"},
}

_STAT_NAMES: dict[str, str] = {
    "ern": "Earning Power",
    "roi": "Return on Investment",
    "res": "AI Resilience",
    "grw": "Growth Potential",
    "aura": "Brand Gravity",
}

_STAT_CONTEXT: dict[str, str] = {
    "ern": "This path pays well for the degree and market you picked.",
    "roi": "The cost of the degree lines up with what you'll earn back.",
    "res": "This career depends on skills AI can't easily replicate.",
    "grw": "The field is expanding — more roles tomorrow than today.",
    "aura": "The school carries real institutional weight in this field.",
}


def _templates_dir() -> Path:
    return project_root() / "backend" / "templates" / "wrapped"


def _base_css() -> str:
    return (_templates_dir() / "_base.css").read_text(encoding="utf-8")


def _jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_templates_dir())),
        autoescape=select_autoescape(["html"]),
    )


def _pentagon_svg(stats: dict[str, int | None]) -> str:
    """Render a pentagon radar chart as inline SVG.

    5 axes at 90°, 162°, 234°, 306°, 18° (ERN top, ROI right,
    RES bottom-right, GRW bottom-left, AURA left). Value 0-10
    scaled to polygon radius. Missing stats treated as 0.
    """
    import math

    size = 780
    cx = size / 2
    cy = size / 2
    r_max = 300

    axes = [
        ("ern", -90, "#F2D477"),
        ("roi", -18, "#7DD4A3"),
        ("res", 54, "#B8A9E8"),
        ("grw", 126, "#7BB8E0"),
        ("aura", 198, "#E8B86B"),
    ]

    def _pt(angle_deg: float, radius: float) -> tuple[float, float]:
        a = math.radians(angle_deg)
        return (cx + radius * math.cos(a), cy + radius * math.sin(a))

    grid_stroke = "rgba(255,255,255,0.08)"
    spoke_stroke = "rgba(255,255,255,0.06)"

    grid_rings: list[str] = []
    for frac in (0.25, 0.5, 0.75, 1.0):
        points = " ".join(
            f"{_pt(a, r_max * frac)[0]:.1f},{_pt(a, r_max * frac)[1]:.1f}"
            for _, a, _ in axes
        )
        grid_rings.append(
            f'<polygon points="{points}" fill="none" '
            f'stroke="{grid_stroke}" stroke-width="1.5"/>'
        )

    spokes: list[str] = []
    for _, a, _ in axes:
        x, y = _pt(a, r_max)
        spokes.append(
            f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" '
            f'stroke="{spoke_stroke}" stroke-width="1"/>'
        )

    poly_pts: list[tuple[float, float]] = []
    for key, angle, _ in axes:
        val = stats.get(key) or 0
        frac = max(0.0, min(1.0, val / 10.0))
        poly_pts.append(_pt(angle, r_max * frac))

    poly_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in poly_pts)

    vertex_dots: list[str] = []
    for (key, _, color), (x, y) in zip(axes, poly_pts):
        vertex_dots.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="10" '
            f'fill="{color}" stroke="#1B1D30" stroke-width="3"/>'
        )

    return f"""
<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">
  {''.join(grid_rings)}
  {''.join(spokes)}
  <polygon points="{poly_str}"
           fill="rgba(125, 212, 163, 0.22)"
           stroke="#7DD4A3"
           stroke-width="3"
           stroke-linejoin="round"/>
  {''.join(vertex_dots)}
</svg>
"""


def _fight_label(boss_id: str) -> str:
    return {
        "ai": "Fight AI",
        "loans": "Student Loans",
        "market": "The Market",
        "burnout": "Burnout",
        "ceiling": "The Ceiling",
    }.get(boss_id, boss_id.title())


def _pick_standout_stat(build: Build) -> str:
    """Return the key of the highest non-null stat, with deterministic tie-break."""
    stats = build.career.stats
    ordered = [
        ("ern", stats.ern),
        ("roi", stats.roi),
        ("res", stats.res),
        ("grw", stats.grw),
        ("aura", stats.aura),
    ]
    # Tie-break: first key wins among equal values → order matters for stability
    best_key = "ern"
    best_val = -1
    for key, val in ordered:
        if val is not None and val > best_val:
            best_val = val
            best_key = key
    return best_key


def _build_context(
    build: Build, profile_name: str, animal_emoji: str
) -> dict[str, dict[str, Any]]:
    """Assemble the per-frame Jinja contexts from a Build."""
    base_css = _base_css()
    profile_display = profile_name if profile_name else "Anonymous Build"

    # Frame 1 (Identity)
    identity_ctx = {
        "base_css": base_css,
        "profile_name_display": f"{profile_display} {animal_emoji}".strip(),
        "profile_emoji": animal_emoji or "✦",
        "school_name": build.school_name,
        "major_text": build.major_text,
    }

    # Frame 2 (Pentagon)
    stats = build.career.stats
    stat_dict = {
        "ern": stats.ern, "roi": stats.roi, "res": stats.res,
        "grw": stats.grw, "aura": stats.aura,
    }
    pentagon_ctx = {
        "base_css": base_css,
        "profile_name_display": profile_display,
        "pentagon_svg": _pentagon_svg(stat_dict),
        "stat_ern": stats.ern if stats.ern is not None else "—",
        "stat_roi": stats.roi if stats.roi is not None else "—",
        "stat_res": stats.res if stats.res is not None else "—",
        "stat_grw": stats.grw if stats.grw is not None else "—",
        "stat_aura": stats.aura if stats.aura is not None else "—",
        "school_name": build.school_name,
        "major_text": build.major_text,
        "career_title": build.career.occupation_title,
    }

    # Frame 3 (Boss Scorecard)
    fights_ctx = []
    for fight in build.gauntlet.fights:
        fights_ctx.append({
            "boss": fight.boss,
            "label": _fight_label(fight.boss),
            "result": fight.result,
            "result_upper": fight.result.upper(),
            "emoji": _BOSS_EMOJI.get(fight.boss, "✦"),
        })
    bosses_ctx = {
        "base_css": base_css,
        "profile_name_display": profile_display,
        "verdict_text": build.gauntlet.verdict or "Build complete",
        "wins": build.gauntlet.wins,
        "losses": build.gauntlet.losses,
        "draws": build.gauntlet.draws,
        "fights": fights_ctx,
    }

    # Frame 4 (Standout insight)
    standout_key = _pick_standout_stat(build)
    standout_val = stat_dict.get(standout_key) or 0
    insight_ctx = {
        "base_css": base_css,
        "profile_name_display": profile_display,
        "stat_value": standout_val,
        "stat_name": _STAT_NAMES[standout_key],
        "stat_color": _STAT_COLORS[standout_key]["base"],
        "halo_color": _STAT_COLORS[standout_key]["halo"],
        "insight_headline": (
            f"Your {_STAT_NAMES[standout_key]} is this build's strongest signal."
        ),
        "insight_context": _STAT_CONTEXT[standout_key],
    }

    # Frame 5 (Biggest Risk / Clean Sweep)
    losses = [f for f in build.gauntlet.fights if f.result == "lose"]
    clean_sweep = len(losses) == 0
    if clean_sweep:
        boss_id = "ai"
        boss_palette = _BOSS_COLORS[boss_id]
        risk_ctx = {
            "base_css": base_css,
            "profile_name_display": profile_display,
            "clean_sweep": True,
            "boss_emoji": "",
            "boss_name": "",
            "result_label": "",
            "narrative": "",
            "skills": [],
            "boss_color": boss_palette["base"],
            "boss_color_strong": boss_palette["strong"],
            "boss_halo_color": boss_palette["halo"],
            "boss_shadow": boss_palette["shadow"],
        }
    else:
        # Pick the loss with the lowest raw_score (worst hit)
        biggest = min(
            losses,
            key=lambda f: f.raw_score if f.raw_score is not None else 0,
        )
        boss_palette = _BOSS_COLORS.get(biggest.boss, _BOSS_COLORS["loans"])
        skills_for_boss = [
            s.title for s in build.skills_crafted if biggest.boss in s.targets
        ]
        fallback_narrative = "This boss hit hardest in your build."
        risk_ctx = {
            "base_css": base_css,
            "profile_name_display": profile_display,
            "clean_sweep": False,
            "boss_emoji": _BOSS_EMOJI.get(biggest.boss, "✦"),
            "boss_name": _fight_label(biggest.boss),
            "result_label": "LOSS",
            "narrative": (
                biggest.narrative or biggest.reason or fallback_narrative
            ),
            "skills": skills_for_boss,
            "boss_color": boss_palette["base"],
            "boss_color_strong": boss_palette["strong"],
            "boss_halo_color": boss_palette["halo"],
            "boss_shadow": boss_palette["shadow"],
        }

    # Frame 6 (CTA)
    cta_ctx = {
        "base_css": base_css,
        "profile_name_display": profile_display,
        "profile_emoji": animal_emoji or "✦",
    }

    return {
        "identity": identity_ctx,
        "pentagon": pentagon_ctx,
        "bosses": bosses_ctx,
        "insight": insight_ctx,
        "risk": risk_ctx,
        "cta": cta_ctx,
    }


_FRAME_ORDER = [
    ("identity", "frame-identity.html"),
    ("pentagon", "frame-pentagon.html"),
    ("bosses", "frame-bosses.html"),
    ("insight", "frame-insight.html"),
    ("risk", "frame-risk.html"),
    ("cta", "frame-cta.html"),
]


async def render_frames(
    build: Build, profile_name: str, animal_emoji: str
) -> list[tuple[int, bytes]]:
    """Render all 6 Wrapped frames and return (index, png_bytes) pairs.

    Launches Chromium once, renders all 6 HTML templates with build
    data, screenshots each at 1080×1920, returns in order.

    Raises:
        RuntimeError: if Playwright is not installed or Chromium is
            not available. The caller should translate to a 500 HTTP
            response — the UI has a mock-mode fallback.
    """
    try:
        from playwright.async_api import (
            async_playwright,  # type: ignore[import-not-found]
        )
    except ImportError as exc:
        raise RuntimeError(
            "playwright is not installed. Run: pip install -e backend && "
            "playwright install chromium"
        ) from exc

    env = _jinja_env()
    contexts = _build_context(build, profile_name, animal_emoji)

    results: list[tuple[int, bytes]] = []
    async with async_playwright() as pw:
        # --disable-dev-shm-usage: containers (incl. Railway) ship with a 64 MB
        # /dev/shm by default, which Chrome will exhaust on a 1080×1920 screenshot
        # and crash with "Target page, context or browser has been closed". Forcing
        # /tmp avoids the shared-memory cliff.
        browser = await pw.chromium.launch(
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        try:
            context = await browser.new_context(
                viewport={"width": 1080, "height": 1920},
                device_scale_factor=1,
            )
            page = await context.new_page()
            for idx, (ctx_key, tmpl_name) in enumerate(_FRAME_ORDER):
                template = env.get_template(tmpl_name)
                html = template.render(**contexts[ctx_key])
                await page.set_content(html, wait_until="networkidle")
                # Wait for @import fonts to finish so Fredoka/Nunito/Space Mono
                # actually land before the screenshot fires.
                await page.evaluate("document.fonts.ready")
                png_bytes = await page.screenshot(type="png", full_page=False)
                results.append((idx, png_bytes))
                logger.info(
                    "Rendered wrapped frame %s (%d bytes)", ctx_key, len(png_bytes)
                )
        finally:
            await browser.close()

    return results
