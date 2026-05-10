"""Salary-consistency audit harness for FutureProof.

Drives 4 school selections through SetYourCourse -> MyBuild -> single PDF,
then 4-build Compare -> Compare PDF, capturing screenshots, scraping salary
text from the DOM, and extracting salary text from the generated PDFs.

Output:
    reports/salary-audit/screenshots/   PNGs per surface
    reports/salary-audit/pdfs/          single + comparison PDFs and .txt dumps
    reports/salary-audit/raw/           per-build JSON dumps of scraped values

The script does NOT auto-start servers. Bring them up first:
    backend:  cd backend && python -m uvicorn app.main:app --port 8000
    frontend: cd frontend && npm run dev   (Vite at :5173)

Re-running the script is safe; output dirs are wiped before each run.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import time
import traceback
from dataclasses import dataclass, field, asdict
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.request import urlopen
from urllib.error import URLError

REPO = Path(__file__).resolve().parent.parent
REPORTS = REPO / "reports" / "salary-audit"
SCREENSHOTS = REPORTS / "screenshots"
PDFS = REPORTS / "pdfs"
RAW = REPORTS / "raw"
FRONTEND = "http://localhost:5173"
BACKEND = "http://localhost:8000"

SCHOOLS: list[dict[str, Any]] = [
    {
        "idx": 1,
        "slug": "iu",
        "school_query": "Indiana University-Bloomington",
        "major": "Marketing",
        "home_state": "IN",
    },
    {
        "idx": 2,
        "slug": "harvard",
        "school_query": "Harvard University",
        "major": "Computer Science",
        "home_state": "MA",
    },
    {
        # Originally Ivy Tech Community College, but Ivy Tech is not in the
        # IPEDS subset shipped in the demo dataset (search returns 0 results
        # for any "Ivy Tech*" variant). Miami Dade College is the substitute
        # community-college pick — same shape (2-year vocational) so we still
        # exercise the program-level earnings_1yr_* fallback path on the
        # CareerCard / Finances surfaces.
        "idx": 3,
        "slug": "miami-dade",
        "school_query": "Miami Dade College",
        "major": "Nursing",
        "home_state": "FL",
    },
    {
        "idx": 4,
        "slug": "caltech",
        "school_query": "California Institute of Technology",
        "major": "Mechanical Engineering",
        "home_state": "CA",
    },
]


@dataclass
class BuildAudit:
    """Per-school audit record."""
    idx: int
    slug: str
    school_query: str
    major: str
    school_name_displayed: str | None = None
    cip_resolved: str | None = None
    career_title: str | None = None
    soc_code: str | None = None
    work_experience_code: int | None = None
    build_id: str | None = None
    set_your_course_card: dict[str, Any] = field(default_factory=dict)
    finances_card: dict[str, Any] = field(default_factory=dict)
    ern_popover: dict[str, Any] = field(default_factory=dict)
    roi_popover: dict[str, Any] = field(default_factory=dict)
    pdf_text: str | None = None
    pdf_dollars: list[str] = field(default_factory=list)
    pdf_pcts: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class CompareAudit:
    """Compare-view + comparison-PDF audit record."""
    builds_in_view: list[str] = field(default_factory=list)
    money_section_text: str | None = None
    money_section_dollars: list[str] = field(default_factory=list)
    pdf_text: str | None = None
    pdf_dollars: list[str] = field(default_factory=list)
    pdf_pcts: list[str] = field(default_factory=list)
    error: str | None = None


# ---------- helpers ----------

DOLLAR_RX = re.compile(r"\$[0-9][0-9,]*(?:\.[0-9]+)?[MKk]?")
PCT_RX = re.compile(r"-?[0-9]+(?:\.[0-9]+)?\s*%")


def find_dollars(text: str) -> list[str]:
    return DOLLAR_RX.findall(text or "")


def find_pcts(text: str) -> list[str]:
    return PCT_RX.findall(text or "")


def reset_dirs() -> None:
    for d in (SCREENSHOTS, PDFS, RAW):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)


def check_servers() -> None:
    for url, name in ((f"{BACKEND}/health", "backend"), (FRONTEND, "frontend")):
        try:
            urlopen(url, timeout=3).read()
        except URLError as exc:
            print(f"[FATAL] {name} not reachable at {url}: {exc}", file=sys.stderr)
            sys.exit(2)
    print("[ok] backend + frontend reachable")


def shot(page: Any, name: str) -> str:
    path = SCREENSHOTS / name
    page.screenshot(path=str(path), full_page=True)
    return path.name


def safe_text(locator: Any) -> str:
    try:
        return (locator.text_content() or "").strip()
    except Exception:
        return ""


def extract_pdf_text(pdf_bytes: bytes) -> str:
    import pypdf
    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


# ---------- profile setup ----------

def setup_profile(page: Any, home_state: str) -> None:
    """Complete /profile so SetYourCourse stops bouncing.

    Profile is per-build (in-memory zustand, no persistence) — every build
    must re-onboard. The `clearProfile()` in AppHeader's "New Build" handler
    wipes the store on purpose. So this is called once per school.
    """
    page.goto(f"{FRONTEND}/profile", wait_until="domcontentloaded")
    page.wait_for_selector("select#home-state", timeout=30_000)
    page.locator("select#home-state").select_option(home_state)
    # Profile screen "Let's go" button — the only Button.variant=primary on the
    # screen, identifiable by aria-label "Continue to school selection".
    page.get_by_label("Continue to school selection").click()
    page.wait_for_url(re.compile(r"/set-your-course"), timeout=15_000)
    page.wait_for_selector("[role='combobox']", timeout=15_000)
    print(f"[ok] profile set up (home_state={home_state})")


# ---------- per-school flow ----------

def pick_school(page: Any, query: str) -> str:
    """Type into school search and pick the first dropdown result. Returns displayed name."""
    # SchoolSearch input is a combobox without a testid; find by role.
    box = page.get_by_role("combobox").first
    box.click()
    box.fill("")
    # Type slowly so the debounced search fires.
    box.type(query, delay=20)
    # Wait for dropdown listbox + at least one option.
    page.wait_for_selector("#school-results [role='option']", timeout=15_000)
    first = page.locator("#school-results [role='option']").first
    name = safe_text(first).split("\n")[0].strip()
    first.click()
    # The combobox is replaced by a div showing the selection; wait for it.
    page.wait_for_selector("[data-testid='major-input']", timeout=10_000)
    return name


def type_major_and_wait_for_outcomes(page: Any, major: str, timeout_ms: int = 90_000) -> None:
    major_input = page.locator("[data-testid='major-input']")
    major_input.click()
    major_input.fill("")
    major_input.type(major, delay=25)
    # Gemma streams; wait first for the streaming card to appear, then for outcomes.
    # If careers already visible (very fast cache hit), skip the streaming wait.
    deadline = time.time() + timeout_ms / 1000.0
    while time.time() < deadline:
        if page.locator("[id^='career-']").count() > 0:
            return
        time.sleep(0.5)
    raise TimeoutError(f"No career outcomes appeared for major={major!r}")


def get_resolved_cip(page: Any) -> str | None:
    """Read the resolved CIP code shown in current-resolution-summary."""
    el = page.locator("[data-testid='current-resolution-summary']")
    if el.count() == 0:
        return None
    text = safe_text(el)
    m = re.search(r"\b\d{2}\.\d{4}\b", text)
    return m.group(0) if m else None


def pick_first_career(page: Any) -> tuple[str, str, dict[str, Any]]:
    """Click first available career card. Returns (soc_code, title, scraped_card_dict)."""
    # Career cards have id="career-{soc_code}" (with a dot in the soc).
    cards = page.locator("[id^='career-']")
    cards.first.scroll_into_view_if_needed()
    first = cards.first
    card_id = first.get_attribute("id") or ""
    soc = card_id[len("career-") :]
    title = safe_text(first.locator("h3").first) or "?"
    raw_text = safe_text(first)

    card_data = {
        "soc_code": soc,
        "title": title,
        "raw_text": raw_text,
        "dollars": find_dollars(raw_text),
        "label_starting_range": "starting range" in raw_text.lower(),
        "label_typical_range": "typical range" in raw_text.lower(),
        "label_year_one": "year one" in raw_text.lower(),
        "label_mid_career": "mid-career" in raw_text.lower(),
    }
    first.click()
    return soc, title, card_data


def commit_build(page: Any) -> None:
    page.locator("[data-testid='btn-spec-build-bottom']").click()
    # Lands on /my-build with build state; wait for finances card or hero.
    page.wait_for_url(re.compile(r"/my-build"), timeout=20_000)
    # Wait for the build to finish loading (action bar appears once build != null).
    page.wait_for_selector("[data-testid='my-build-action-bar']", timeout=120_000)


def scrape_finances(page: Any) -> dict[str, Any]:
    """Read every salary/cost label+value visible on the FinancesCard."""
    region = page.get_by_role("region", name=re.compile(r"finances|money", re.I)).first
    if region.count() == 0:
        # Fallback: the card has aria-label='Finances'.
        region = page.locator("[aria-label='Finances'], [aria-label='finances']").first
    raw_text = safe_text(region) if region.count() else ""
    return {
        "raw_text": raw_text,
        "dollars": find_dollars(raw_text),
        "pcts": find_pcts(raw_text),
        "has_mid_career": "mid-career" in raw_text.lower(),
        "has_year_one": "year-one" in raw_text.lower() or "year one" in raw_text.lower(),
        "has_starting_range": "starting range" in raw_text.lower(),
        "has_typical_range": "salary range" in raw_text.lower() or "typical range" in raw_text.lower(),
        "has_published_cost": "published" in raw_text.lower() or "4-year" in raw_text.lower(),
    }


def open_stat_popover(page: Any, stat_key: str) -> dict[str, Any]:
    """Click the ? button next to the named stat and capture the popover text.

    BuildResultsScreen renders aria-label="What is Earning Power?" / "What is
    Return on Investment?" etc. — the literal stat.name (not the localized
    nameKey), per data/statExplanations.ts.
    """
    aria_name = {
        "ern": "What is Earning Power?",
        "roi": "What is Return on Investment?",
    }[stat_key]
    btn = page.get_by_label(aria_name, exact=True).first
    if btn.count() == 0:
        return {"opened": False, "raw_text": "", "dollars": [], "error": "button-not-found"}
    btn.scroll_into_view_if_needed()
    btn.click()
    try:
        page.wait_for_selector(f"#info-{stat_key}", timeout=5_000)
    except Exception as e:
        return {"opened": False, "raw_text": "", "dollars": [], "error": f"popover-not-shown: {e}"}
    pop = page.locator(f"#info-{stat_key}")
    raw_text = safe_text(pop)
    out = {
        "opened": True,
        "raw_text": raw_text,
        "dollars": find_dollars(raw_text),
        "mentions_year_one": "year-1" in raw_text.lower() or "year 1" in raw_text.lower() or "year one" in raw_text.lower(),
        "mentions_starting_salary": "starting salary" in raw_text.lower(),
        "mentions_4yr_cost": "4-year" in raw_text.lower() or "4 year" in raw_text.lower() or "published" in raw_text.lower(),
    }
    return out


def close_popover(page: Any) -> None:
    page.keyboard.press("Escape")
    time.sleep(0.15)


def save_build(page: Any) -> str | None:
    """Click Save on the action bar. Returns the build_id from the URL after save."""
    btn = page.locator("[data-testid='btn-save-build-bar']")
    if btn.count() == 0:
        return None
    btn.click()
    # Wait until button text becomes "Saved" or it stops disabled.
    for _ in range(60):
        text = safe_text(btn).lower()
        if "saved" in text:
            break
        time.sleep(0.25)
    # Build id is in the URL path /my-build (the build store carries it). Pull
    # from window.location or buildStore via API.
    url = page.url
    return url


def export_single_pdf(page: Any) -> bytes | None:
    """Click the export PDF button and capture the download bytes."""
    btn = page.locator("[data-testid='btn-export-pdf-build']")
    if btn.count() == 0:
        return None
    btn.scroll_into_view_if_needed()
    with page.expect_download(timeout=120_000) as dl_info:
        btn.click()
    download = dl_info.value
    tmp = PDFS / f"_dl_{int(time.time())}.pdf"
    download.save_as(str(tmp))
    data = tmp.read_bytes()
    tmp.unlink()
    return data


# ---------- compare flow ----------

def run_compare(page: Any) -> CompareAudit:
    """Navigate to /builds via SPA — page.goto() reloads the bundle and
    wipes the in-memory profile store, which forces a redirect back to
    /profile (MenuScreen requires a profile in memory). Use the AppHeader's
    `header-compare` button to push the route via react-router."""
    audit = CompareAudit()
    page.locator("[data-testid='header-compare']").click()
    page.wait_for_url(re.compile(r"/builds.*select=1"), timeout=10_000)
    page.wait_for_selector("[data-testid='region-saved-builds']", timeout=20_000)

    cards = page.locator("[data-testid^='card-build-']")
    n = cards.count()
    print(f"[compare] {n} build cards visible")
    audit.builds_in_view = [
        cards.nth(i).get_attribute("data-testid") or "" for i in range(n)
    ]
    # Click up to first 4 to select.
    for i in range(min(n, 4)):
        cards.nth(i).click()
        time.sleep(0.1)

    page.locator("[data-testid='btn-compare']").click()
    page.wait_for_selector("[data-testid='region-compare']", timeout=20_000)
    time.sleep(2)  # let layout settle / pivotal insights load
    shot(page, "05-compare-table.png")

    # Money section.
    money = page.locator("[data-testid='money-section']").first
    if money.count():
        money.scroll_into_view_if_needed()
        time.sleep(0.5)
        shot(page, "06-compare-money.png")
        text = safe_text(money)
        audit.money_section_text = text
        audit.money_section_dollars = find_dollars(text)

    # Export comparison PDF.
    btn = page.locator("[data-testid='btn-export-pdf-compare']")
    if btn.count():
        btn.scroll_into_view_if_needed()
        try:
            with page.expect_download(timeout=180_000) as dl_info:
                btn.click()
            download = dl_info.value
            tmp = PDFS / "_dl_compare.pdf"
            download.save_as(str(tmp))
            data = tmp.read_bytes()
            tmp.unlink()
            (PDFS / "compare.pdf").write_bytes(data)
            text = extract_pdf_text(data)
            (PDFS / "compare.txt").write_text(text, encoding="utf-8")
            audit.pdf_text = text
            audit.pdf_dollars = find_dollars(text)
            audit.pdf_pcts = find_pcts(text)
        except Exception as e:
            audit.error = f"compare-pdf-export-failed: {e}"
    else:
        audit.error = "compare-pdf-button-missing"
    return audit


# ---------- per-school orchestration ----------

def run_school(page: Any, cfg: dict[str, Any]) -> BuildAudit:
    audit = BuildAudit(idx=cfg["idx"], slug=cfg["slug"], school_query=cfg["school_query"], major=cfg["major"])
    try:
        # setup_profile() leaves us on /set-your-course with combobox visible.
        setup_profile(page, cfg["home_state"])
        audit.school_name_displayed = pick_school(page, cfg["school_query"])
        print(f"  [{cfg['slug']}] school = {audit.school_name_displayed}")

        type_major_and_wait_for_outcomes(page, cfg["major"])
        audit.cip_resolved = get_resolved_cip(page)
        print(f"  [{cfg['slug']}] resolved cip = {audit.cip_resolved}")

        time.sleep(0.5)
        shot(page, f"{cfg['idx']:02d}-{cfg['slug']}-set-your-course.png")

        soc, title, card = pick_first_career(page)
        audit.soc_code = soc
        audit.career_title = title
        audit.set_your_course_card = card
        print(f"  [{cfg['slug']}] career = {title} (SOC {soc})")
        time.sleep(0.4)

        commit_build(page)
        time.sleep(1.0)
        shot(page, f"{cfg['idx']:02d}-{cfg['slug']}-my-build.png")

        # Find finances area; scroll to it for the screenshot.
        # FinancesCard renders inside a region with aria-label="Finances".
        try:
            page.locator("[aria-label='Finances']").first.scroll_into_view_if_needed()
            time.sleep(0.3)
            shot(page, f"{cfg['idx']:02d}-{cfg['slug']}-finances.png")
        except Exception:
            pass
        audit.finances_card = scrape_finances(page)

        # ERN popover + screenshot.
        try:
            audit.ern_popover = open_stat_popover(page, "ern")
            time.sleep(0.2)
            shot(page, f"{cfg['idx']:02d}-{cfg['slug']}-ern-popover.png")
            close_popover(page)
        except Exception as e:
            audit.ern_popover = {"opened": False, "error": str(e)}

        # ROI popover + screenshot.
        try:
            audit.roi_popover = open_stat_popover(page, "roi")
            time.sleep(0.2)
            shot(page, f"{cfg['idx']:02d}-{cfg['slug']}-roi-popover.png")
            close_popover(page)
        except Exception as e:
            audit.roi_popover = {"opened": False, "error": str(e)}

        # Save the build (so it appears in /builds for compare).
        save_build(page)
        time.sleep(0.5)

        # Export single PDF.
        try:
            pdf = export_single_pdf(page)
            if pdf:
                (PDFS / f"{cfg['idx']:02d}-{cfg['slug']}.pdf").write_bytes(pdf)
                text = extract_pdf_text(pdf)
                (PDFS / f"{cfg['idx']:02d}-{cfg['slug']}.txt").write_text(text, encoding="utf-8")
                audit.pdf_text = text
                audit.pdf_dollars = find_dollars(text)
                audit.pdf_pcts = find_pcts(text)
            else:
                audit.error = "no-pdf-button"
        except Exception as e:
            audit.error = f"pdf-export-failed: {e}"
            traceback.print_exc()

        # Pull build_id from URL or local storage if available.
        try:
            audit.build_id = page.evaluate("() => window.location.pathname")
        except Exception:
            pass
    except Exception as e:
        audit.error = f"flow-failed: {e}"
        traceback.print_exc()
        try:
            shot(page, f"{cfg['idx']:02d}-{cfg['slug']}-ERROR.png")
        except Exception:
            pass
    return audit


# ---------- main ----------

def main() -> int:
    check_servers()
    reset_dirs()

    from playwright.sync_api import sync_playwright

    audits: list[BuildAudit] = []
    compare: CompareAudit | None = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 1024}, accept_downloads=True)
        page = ctx.new_page()

        # Step 1: 4 schools (each calls setup_profile internally).
        for cfg in SCHOOLS:
            print(f"--- school {cfg['idx']}: {cfg['school_query']} / {cfg['major']} ---")
            audit = run_school(page, cfg)
            audits.append(audit)
            (RAW / f"{cfg['idx']:02d}-{cfg['slug']}.json").write_text(
                json.dumps(asdict(audit), indent=2), encoding="utf-8"
            )

        # Step 3: compare.
        try:
            compare = run_compare(page)
            (RAW / "compare.json").write_text(json.dumps(asdict(compare), indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[compare] failed: {e}", file=sys.stderr)
            traceback.print_exc()

        ctx.close()
        browser.close()

    # Step 4: dump combined raw record.
    summary = {
        "schools": [asdict(a) for a in audits],
        "compare": asdict(compare) if compare else None,
    }
    (RAW / "_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("[done] raw outputs in", RAW)
    return 0


if __name__ == "__main__":
    sys.exit(main())
