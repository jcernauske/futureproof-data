"""Record a frame-perfect 60fps MP4 of the title card.

Uses Chrome DevTools Protocol's Emulation.setVirtualTimePolicy to advance
the page's clock in deterministic 16.667ms ticks (1/60s), capturing one
PNG per frame. ffmpeg then assembles the sequence into an H.264 MP4.

This is the same trick Puppeteer animation-snapshot recipes use — virtual
time controls performance.now(), document.timeline, and therefore every
CSS animation on the page. Real wall-clock latency of page.screenshot()
is irrelevant because no animation ticks while we're capturing.

Usage:
    uv run python scripts/record_title_card.py
    uv run python scripts/record_title_card.py --seconds 12 --fps 60

Output:
    video/title-card/frames/frame_NNNN.png   (raw PNG sequence)
    video/title-card/title-card.mp4          (H.264 mp4, yuv420p, crf 18)
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import subprocess
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PAGE = REPO_ROOT / "docs" / "video" / "kinetic" / "brand-reveal-v2.html"
OUTPUT_DIR = REPO_ROOT / "video" / "title-card"
FRAMES_DIR = OUTPUT_DIR / "frames"


async def record(page_path: Path, seconds: float, fps: int) -> None:
    frame_ms = 1000.0 / fps
    total_frames = int(round(seconds * fps))
    print(f"recording {seconds:.2f}s @ {fps}fps = {total_frames} frames")
    print(f"frame interval: {frame_ms:.4f}ms (virtual time)")

    if FRAMES_DIR.exists():
        shutil.rmtree(FRAMES_DIR)
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
        )
        page = await context.new_page()
        cdp = await context.new_cdp_session(page)

        # Load page with real wall-clock time so Google Fonts + any other
        # network fetches finish. Virtual time interferes with the network
        # stack so we apply it AFTER the page is settled.
        url = f"file://{page_path.resolve()}"
        print(f"loading {url}")
        await page.goto(url, wait_until="load")

        # Wait for fonts + any deferred work to settle.
        await page.evaluate("() => document.fonts.ready")
        await asyncio.sleep(0.3)

        # Now freeze the document timeline at virtual t=0 and reset every
        # animation to its first frame. From here on, time only moves when
        # we tell it to.
        await cdp.send("Emulation.setVirtualTimePolicy", {"policy": "pause"})
        await page.evaluate(
            """() => {
                document.getAnimations().forEach((anim) => {
                    try {
                        anim.currentTime = 0;
                        anim.startTime = 0;
                    } catch (e) { /* some anims are read-only */ }
                });
            }"""
        )

        # Now drive the timeline frame-by-frame. The listener MUST be
        # attached before each setVirtualTimePolicy call to avoid losing
        # the budget-expired event in a race.
        wall_start = time.perf_counter()
        loop = asyncio.get_event_loop()
        for frame_idx in range(total_frames):
            expired_future: asyncio.Future[None] = loop.create_future()

            def _on_expired(_payload: dict, fut=expired_future) -> None:
                if not fut.done():
                    fut.set_result(None)

            cdp.on("Emulation.virtualTimeBudgetExpired", _on_expired)
            try:
                await cdp.send(
                    "Emulation.setVirtualTimePolicy",
                    {"policy": "advance", "budget": frame_ms},
                )
                await asyncio.wait_for(expired_future, timeout=5.0)
            finally:
                cdp.remove_listener(
                    "Emulation.virtualTimeBudgetExpired", _on_expired
                )

            frame_path = FRAMES_DIR / f"frame_{frame_idx:04d}.png"
            await page.screenshot(
                path=str(frame_path),
                clip={"x": 0, "y": 0, "width": 1920, "height": 1080},
                animations="allow",
            )

            if frame_idx % 30 == 0:
                elapsed = time.perf_counter() - wall_start
                print(
                    f"  frame {frame_idx:4d}/{total_frames}  "
                    f"({elapsed:.1f}s elapsed, "
                    f"{(frame_idx + 1) / max(elapsed, 0.001):.1f}fps capture)"
                )

        wall_elapsed = time.perf_counter() - wall_start
        print(f"captured {total_frames} frames in {wall_elapsed:.1f}s")

        await browser.close()


def assemble_mp4(fps: int) -> Path:
    output = OUTPUT_DIR / "title-card.mp4"
    if output.exists():
        output.unlink()

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "warning",
        "-framerate", str(fps),
        "-i", str(FRAMES_DIR / "frame_%04d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        "-preset", "slow",
        "-movflags", "+faststart",
        str(output),
    ]
    print("assembling mp4:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"wrote {output}  ({output.stat().st_size / 1_000_000:.1f} MB)")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--page",
        type=Path,
        default=DEFAULT_PAGE,
        help="HTML page to record (default: docs/video/kinetic/brand-reveal-v2.html)",
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=8.0,
        help="Recording duration in seconds (default: 8.0)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=60,
        help="Frame rate (default: 60)",
    )
    parser.add_argument(
        "--no-mp4",
        action="store_true",
        help="Skip ffmpeg assembly — leave PNG sequence only",
    )
    args = parser.parse_args()

    if not args.page.exists():
        print(f"ERROR: page not found: {args.page}", file=sys.stderr)
        return 2
    if shutil.which("ffmpeg") is None and not args.no_mp4:
        print("ERROR: ffmpeg not on PATH", file=sys.stderr)
        return 2

    asyncio.run(record(args.page, args.seconds, args.fps))

    if not args.no_mp4:
        assemble_mp4(args.fps)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
