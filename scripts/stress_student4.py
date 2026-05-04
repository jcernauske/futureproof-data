"""
Student 4 — The Edge Case Explorer
Home: NY | 4 builds designed to hit data edges

Harness fixes from Round 3:
1. Slider selectors: [role='slider'][aria-label='...'] + keyboard arrows
2. Null-stat extraction: per-stat regex handling em-dash
3. Search workaround: search shorter parent name, pick campus from dropdown

Build 1: "University of California" -> Los Angeles -> "film" (effort=All-in, loans=Some)
Build 2: "community" -> whatever CC appears -> "nursing" (effort=Working + school, loans=Half)
Build 3: "Harvard" -> "philosophy" (effort=Balanced, loans=No loans)
Build 4: "Ohio State" -> Main Campus -> "computer science" (effort=Strong focus, loans=Mostly)
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request
from playwright.sync_api import sync_playwright

API_BASE = "http://localhost:8000"
SCREENSHOT_DIR = "reports/screenshots"
SCREENSHOT_MD_PREFIX = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

EFFORT_STOPS = ["Working two jobs", "Working + school", "Balanced", "Strong focus", "All-in"]
LOAN_STOPS = ["No loans", "Some", "Half", "Mostly", "All loans"]

BUILDS_CONFIG = [
    {
        "search_term": "University of California",
        "match_text": "Los Angeles",
        "major": "film",
        "effort_idx": 4,
        "loan_idx": 1,
        "label": "UCLA + film",
    },
    {
        "search_term": "community",
        "match_text": None,
        "major": "nursing",
        "effort_idx": 1,
        "loan_idx": 2,
        "label": "Community college + nursing",
    },
    {
        "search_term": "Harvard",
        "match_text": "Harvard",
        "major": "philosophy",
        "effort_idx": 2,
        "loan_idx": 0,
        "label": "Harvard + philosophy",
    },
    {
        "search_term": "Ohio State",
        "match_text": "Main Campus",
        "major": "computer science",
        "effort_idx": 3,
        "loan_idx": 3,
        "label": "Ohio State Main + CS",
    },
]

SKIP_CAREERS = [
    "chief executive", "chief officer", "executive director",
    "postsecondary", "professor",
]

findings = []
builds_data = []
search_notes = []


def log(msg):
    findings.append(msg)
    print(msg)


def salary_to_num(s):
    return int(s.replace("$", "").replace(",", ""))


def set_effort(page, target_idx):
    slider = page.locator("[role='slider'][aria-label='Effort level']")
    slider.focus()
    for _ in range(4):
        slider.press("ArrowLeft")
    for _ in range(target_idx):
        slider.press("ArrowRight")
    page.wait_for_timeout(500)
    actual = slider.get_attribute("aria-valuetext")
    log(f"  - Effort set to: {actual} (index {target_idx})")
    return actual


def set_loans(page, target_idx):
    slider = page.locator("[role='slider'][aria-label='Loan percentage']")
    slider.focus()
    for _ in range(4):
        slider.press("ArrowLeft")
    for _ in range(target_idx):
        slider.press("ArrowRight")
    page.wait_for_timeout(500)
    actual = slider.get_attribute("aria-valuetext")
    log(f"  - Loans set to: {actual} (index {target_idx})")
    return actual


def extract_career_cards(page):
    cards = []
    for btn in page.locator("button").all():
        try:
            text = btn.inner_text(timeout=3000)
        except Exception:
            continue
        if "/yr median" not in text or "ERN" not in text:
            continue
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        salary = ""
        stats = {}
        title = ""
        for i, line in enumerate(lines):
            if "/yr median" in line:
                salary = line.replace("/yr median", "").strip()
            elif line in ("ERN", "ROI", "RES", "GRW", "AURA") and i + 1 < len(lines):
                try:
                    stats[line] = int(lines[i + 1])
                except ValueError:
                    stats[line] = lines[i + 1]
        for line in lines:
            if (line and not line.startswith("$") and "/yr" not in line
                    and line not in ("ERN", "ROI", "RES", "GRW", "AURA", "\U0001f9ed", "\U0001f4ca", "\U0001f4da",
                                     "Common", "Stretch", "---", "SELECTED")
                    and len(line) > 3):
                try:
                    int(line)
                except ValueError:
                    title = line
                    break
        if title and salary:
            cards.append({"title": title, "salary": salary, "stats": stats, "element": btn})
    return cards


def extract_syc_financials(page):
    text = page.inner_text("body")
    data = {}
    m = re.search(r"financing\s+(\d+)%\s+of\s+\$([\d,]+)", text)
    if m:
        data["financing_pct"] = m.group(1)
        data["published_cost_4yr"] = m.group(2).replace(",", "")
    m = re.search(r"At\s+\d+%:\s+\$([\d,]+)\s+in loans", text)
    if m:
        data["modeled_debt"] = m.group(1).replace(",", "")
    if "no debt" in text.lower() or "auto-win" in text.lower():
        data["modeled_debt"] = "0"
        if "financing_pct" not in data:
            data["financing_pct"] = "0"
    return data


def extract_build_results(page):
    text = page.inner_text("body")
    data = {}

    for stat in ["ERN", "ROI", "RES", "GRW", "AURA"]:
        m = re.search(rf'{stat}\n(\d+|—)', text)
        if m:
            val = m.group(1)
            data[f"stat_{stat}"] = None if val == "—" else int(val)

    for field, pattern in [
        ("starting_salary", r'Starting salary\n\$([\d,]+)'),
        ("median_salary", r'Median salary\n\$([\d,]+)'),
        ("published_cost_4yr", r'Published cost \(4 yr\)\n\$([\d,]+)'),
        ("net_price_4yr", r'Avg\. net price \(4 yr\)\n\$([\d,]+)'),
        ("modeled_debt", r'Modeled debt\n\$([\d,]+)'),
        ("program_median_debt", r'Program median debt\n\$([\d,]+)'),
        ("financing_pct", r'Financing\n(\d+)%'),
    ]:
        m = re.search(pattern, text)
        if m:
            data[field] = m.group(1).replace(",", "")

    if "modeled_debt" not in data and "no debt" in text.lower():
        data["modeled_debt"] = "0"

    boss_map = {"vs. AI": "AI", "vs. Student Loans": "Loans", "vs. The Market": "Market",
                "vs. Burnout": "Burnout", "vs. The Ceiling": "Ceiling"}
    for pattern, boss_key in boss_map.items():
        idx = text.find(pattern)
        if idx >= 0:
            nearby = text[idx:idx + 300]
            for outcome in ["VICTORY", "STANDOFF", "DEFEATED"]:
                if outcome in nearby:
                    data[f"boss_{boss_key}"] = outcome
                    break

    m = re.search(r'(\d+) of 5 victories?\s*·\s*(\d+) standoffs?\s*·\s*(\d+) defeats?', text)
    if m:
        data["wins"] = int(m.group(1))
        data["standoffs"] = int(m.group(2))
        data["defeats"] = int(m.group(3))

    return data


def cross_check(syc_data, card_data, results_data):
    checks = []
    for field in ["published_cost_4yr", "modeled_debt"]:
        if field in syc_data and field in results_data:
            if syc_data[field] != results_data[field]:
                checks.append(f"[WRONG NUMBER] {field}: SYC=${syc_data[field]} vs Results=${results_data[field]}")
            else:
                checks.append(f"{field} consistent: ${results_data[field]}")

    card_salary = card_data.get("salary", "").replace("$", "").replace(",", "")
    if card_salary and "median_salary" in results_data:
        if card_salary != results_data["median_salary"]:
            checks.append(f"[WRONG NUMBER] median_salary: card=${card_salary} vs Results=${results_data['median_salary']}")
        else:
            checks.append(f"median_salary consistent: ${results_data['median_salary']}")

    for stat in ["ERN", "ROI", "RES", "GRW", "AURA"]:
        cv = card_data.get("stats", {}).get(stat)
        rv = results_data.get(f"stat_{stat}")
        if isinstance(cv, int) and isinstance(rv, int):
            if cv != rv:
                checks.append(f"[WRONG NUMBER] {stat}: card={cv} vs Results={rv}")
            else:
                checks.append(f"{stat} consistent: {rv}")
    return checks


def do_build(page, config, build_num, is_first):
    search_term = config["search_term"]
    match_text = config["match_text"]
    major = config["major"]
    effort_idx = config["effort_idx"]
    loan_idx = config["loan_idx"]
    label = config["label"]

    log(f"\n### Build {build_num} — {label}")
    log(f"- Target: search \"{search_term}\"{f', pick \"{match_text}\"' if match_text else ''}, major \"{major}\"")
    log(f"- Sliders: effort={EFFORT_STOPS[effort_idx]} ({effort_idx}), loans={LOAN_STOPS[loan_idx]} ({loan_idx})")

    # Navigate to SYC
    if not is_first:
        if "/my-build" in page.url:
            start_over = page.locator("text=Start over")
            if start_over.count() > 0:
                start_over.first.click()
                page.wait_for_timeout(3000)
            yes_btn = page.locator("text=Yes, start over")
            if yes_btn.count() > 0:
                yes_btn.click()
                page.wait_for_timeout(2000)

    try:
        page.locator("input[placeholder*='Search for your school']").wait_for(timeout=10000)
    except Exception:
        log(f"- [CRASH] School search not found. URL: {page.url}")
        page.screenshot(path=f"{SCREENSHOT_DIR}/s4_b{build_num}_stuck.png", full_page=True)
        return None

    # --- SCHOOL SEARCH (with workaround logging) ---
    search = page.locator("input[placeholder*='Search for your school']")
    search.fill(search_term)
    try:
        page.locator("[role='option']").first.wait_for(timeout=7000)
    except Exception:
        log(f"- [SEARCH] No results for '{search_term}', trying shorter query...")
        shorter = " ".join(search_term.split()[:2])
        search.fill(shorter)
        try:
            page.locator("[role='option']").first.wait_for(timeout=5000)
        except Exception:
            log(f"- [SEARCH FAIL] No results for '{shorter}' either")
            page.screenshot(path=f"{SCREENSHOT_DIR}/s4_b{build_num}_nosearch.png", full_page=True)
            return None

    options = page.locator("[role='option']").all()
    option_texts = []
    for opt in options:
        try:
            option_texts.append(opt.inner_text().strip())
        except Exception:
            option_texts.append("(unreadable)")

    log(f"  - Search '{search_term}' returned {len(option_texts)} results: {option_texts[:8]}")
    search_notes.append({
        "build": build_num,
        "search_term": search_term,
        "match_target": match_text,
        "results_count": len(option_texts),
        "results": option_texts[:8],
    })

    actual_school = ""
    if match_text:
        for i, text in enumerate(option_texts):
            if match_text.lower() in text.lower():
                actual_school = text
                options[i].click()
                search_notes[-1]["matched"] = True
                search_notes[-1]["picked"] = text
                break
        else:
            if option_texts:
                actual_school = option_texts[0]
                options[0].click()
                log(f"- [SEARCH FAIL] Wanted '{match_text}', picked first: {actual_school}")
                search_notes[-1]["matched"] = False
                search_notes[-1]["picked"] = actual_school
            else:
                log(f"- [SEARCH FAIL] No results at all")
                return None
    else:
        if option_texts:
            actual_school = option_texts[0]
            options[0].click()
            search_notes[-1]["matched"] = True
            search_notes[-1]["picked"] = actual_school
            log(f"- [SEARCH] Picked first available: {actual_school}")
        else:
            log(f"- [SEARCH FAIL] No results")
            return None

    log(f"- School: {actual_school}")
    page.wait_for_timeout(2000)

    # --- MAJOR ---
    major_input = page.locator("input[placeholder*='studying' i]")
    major_input.first.fill(major)
    log(f'- Major: "{major}"')

    # --- WAIT FOR CAREER CARDS ---
    cards = []
    for attempt in range(12):
        page.wait_for_timeout(5000)
        cards = extract_career_cards(page)
        if cards:
            break

    if not cards:
        log(f"- [NO CAREERS] No career cards after 60s for \"{major}\" at {actual_school}")
        page.screenshot(path=f"{SCREENSHOT_DIR}/s4_b{build_num}_no_careers.png", full_page=True)
        return None

    log(f"- Careers shown: {len(cards)}")

    # --- SET SLIDERS ---
    set_effort(page, effort_idx)
    set_loans(page, loan_idx)
    page.wait_for_timeout(1000)

    # Re-extract cards after slider change
    cards = extract_career_cards(page)

    # --- PICK CAREER (mid-range, excluding executive roles) ---
    realistic = [c for c in cards if not any(s in c["title"].lower() for s in SKIP_CAREERS)]
    if not realistic:
        realistic = cards
    realistic.sort(key=lambda c: salary_to_num(c["salary"]))
    best = realistic[len(realistic) // 2]
    best["element"].click()
    page.wait_for_timeout(1000)

    log(f"- **Career:** {best['title']} ({best['salary']}/yr)")
    stat_str = " ".join(f"{s}={best['stats'].get(s, '?')}" for s in ["ERN", "ROI", "RES", "GRW", "AURA"])
    log(f"  - Card stats: {stat_str}")

    # --- SYC FINANCIALS ---
    syc_data = extract_syc_financials(page)
    log(f"  - SYC financials: cost_4yr=${syc_data.get('published_cost_4yr', '?')} debt=${syc_data.get('modeled_debt', '?')} financing={syc_data.get('financing_pct', '?')}%")

    page.screenshot(path=f"{SCREENSHOT_DIR}/s4_b{build_num}_setyourcourse.png", full_page=True)
    log(f"\n**Set Your Course:**\n![SYC]({SCREENSHOT_MD_PREFIX}/s4_b{build_num}_setyourcourse.png)\n")

    # --- BUILD ---
    build_btn = None
    for b in page.locator("button").all():
        try:
            if "spec my build" in b.inner_text().lower():
                build_btn = b
                break
        except Exception:
            pass
    if not build_btn:
        log("- [CRASH] No build button")
        return None

    build_btn.scroll_into_view_if_needed()
    build_btn.click()
    log("- Building...")

    page.wait_for_timeout(15000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(5000)

    if "/my-build" not in page.url:
        log(f"- [CRASH] Expected /my-build, got {page.url}")
        page.screenshot(path=f"{SCREENSHOT_DIR}/s4_b{build_num}_crash.png", full_page=True)
        return None

    # --- REVEAL BOSSES ---
    for btn in page.locator("text=TAP TO REVEAL").all():
        try:
            btn.scroll_into_view_if_needed()
            btn.click()
            page.wait_for_timeout(800)
        except Exception:
            pass
    page.wait_for_timeout(2000)

    page.screenshot(path=f"{SCREENSHOT_DIR}/s4_b{build_num}_results.png", full_page=True)
    log(f"\n**Build Results:**\n![Results]({SCREENSHOT_MD_PREFIX}/s4_b{build_num}_results.png)\n")

    # --- EXTRACT RESULTS ---
    results_data = extract_build_results(page)

    log("- **Results data:**")
    log(f"  - Starting salary: ${results_data.get('starting_salary', '?')} | Median: ${results_data.get('median_salary', '?')}")
    log(f"  - Cost 4yr: ${results_data.get('published_cost_4yr', '?')} | Net price: ${results_data.get('net_price_4yr', '?')}")
    log(f"  - Modeled debt: ${results_data.get('modeled_debt', '?')} | Program median debt: ${results_data.get('program_median_debt', '?')}")
    log(f"  - Financing: {results_data.get('financing_pct', '?')}%")

    stat_str = " ".join(f"{s}={results_data.get(f'stat_{s}', '?')}" for s in ["ERN", "ROI", "RES", "GRW", "AURA"])
    log(f"  - Pentagon: {stat_str}")

    boss_str = " | ".join(f"{b}={results_data.get(f'boss_{b}', '?')}" for b in ["AI", "Loans", "Market", "Burnout", "Ceiling"])
    log(f"  - Bosses: {boss_str}")

    if results_data.get("wins") is not None:
        log(f"  - Record: {results_data['wins']}W / {results_data.get('standoffs', 0)}S / {results_data.get('defeats', 0)}D")

    # Pentagon rendered?
    stats_found = sum(1 for s in ["ERN", "ROI", "RES", "GRW", "AURA"] if f"stat_{s}" in results_data)
    log(f"  - Pentagon stats extracted: {stats_found}/5")

    log("- **SYC vs Results consistency:**")
    for check in cross_check(syc_data, best, results_data):
        log(f"  - {check}")

    builds_data.append({
        "build_num": build_num,
        "school": actual_school,
        "major": major,
        "career": best["title"],
        "card": best,
        "syc": syc_data,
        "results": results_data,
        "effort_idx": effort_idx,
        "effort_label": EFFORT_STOPS[effort_idx],
        "loan_idx": loan_idx,
        "loan_label": LOAN_STOPS[loan_idx],
        "label": label,
    })
    return True


# ===== MAIN =====
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    log("## Student #4: The Edge Case Explorer")
    log("- **Persona:** New York kid, testing the weirdest paths")
    log("- **Strategy:** 4 builds designed to hit data edges")
    log("  - Build 1: UCLA + film (arts major at research university)")
    log("  - Build 2: Community college + nursing (sparsest school we can find)")
    log("  - Build 3: Harvard + philosophy (expensive private + humanities)")
    log("  - Build 4: Ohio State Main + computer science (retry Round 2 fail)")

    # --- CREATE PROFILE (NY) ---
    page.goto("http://localhost:5173/profile")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(4000)
    profile_name = page.locator("h1, h2").first.inner_text().strip()
    log(f"\n**Profile:** {profile_name} | Home: NY")
    page.select_option("#home-state", "NY")
    page.locator("text=Let's go").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # --- 4 BUILDS ---
    for i, config in enumerate(BUILDS_CONFIG):
        try:
            do_build(page, config, i + 1, is_first=(i == 0))
        except Exception as e:
            log(f"\n### Build {i + 1}\n- [CRASH] {e}")

    # --- SEARCH WORKAROUND NOTES ---
    log("\n---\n### Search Workaround Notes")
    log("")
    log("| Build | Search Term | Target | Results | Matched? | Actually Picked |")
    log("|-------|-------------|--------|---------|----------|-----------------|")
    for sn in search_notes:
        matched_str = "✓" if sn.get("matched") else "✗"
        log(f"| {sn['build']} | \"{sn['search_term']}\" | {sn.get('match_target', 'any')} | {sn['results_count']} | {matched_str} | {sn.get('picked', '?')[:35]} |")

    # --- CROSS-BUILD COMPARISON ---
    log("\n---\n### Cross-Build Comparison")
    log("")
    log("| # | School | Major | Career | ERN | ROI | RES | GRW | AURA | Cost 4yr | Debt | Effort | Loans | Record |")
    log("|---|--------|-------|--------|-----|-----|-----|-----|------|----------|------|--------|-------|--------|")
    for b in builds_data:
        r = b["results"]
        record = f"{r.get('wins', '?')}W-{r.get('standoffs', '?')}S-{r.get('defeats', '?')}D"
        ern = r.get("stat_ERN")
        ern_s = "—" if ern is None else str(ern)
        roi = r.get("stat_ROI")
        roi_s = "—" if roi is None else str(roi)
        res = r.get("stat_RES")
        res_s = "—" if res is None else str(res)
        grw = r.get("stat_GRW")
        grw_s = "—" if grw is None else str(grw)
        aura = r.get("stat_AURA")
        aura_s = "—" if aura is None else str(aura)
        log(f"| {b['build_num']} | {b['school'][:22]} | {b['major'][:12]} | {b['career'][:22]} | {ern_s} | {roi_s} | {res_s} | {grw_s} | {aura_s} | ${r.get('published_cost_4yr', '?')} | ${r.get('modeled_debt', '?')} | {b['effort_label'][:10]} | {b['loan_label'][:8]} | {record} |")

    # --- SUMMARY ---
    log("\n---\n### Round 4 Summary")
    log("")
    log(f"- **Student #3 builds completed:** (see above)")
    log(f"- **Student #4 builds attempted:** {len(BUILDS_CONFIG)}")
    log(f"- **Student #4 builds completed:** {len(builds_data)}")
    log(f"- **Student #4 builds failed:** {len(BUILDS_CONFIG) - len(builds_data)}")

    # Pentagon rendering check
    all_pentagons_ok = all(
        sum(1 for s in ["ERN", "ROI", "RES", "GRW", "AURA"] if f"stat_{s}" in b["results"]) >= 3
        for b in builds_data
    )
    log(f"- **Pentagon rendered for every build:** {'Yes' if all_pentagons_ok else 'No — check individual builds'}")

    # Any crashes on sparse data?
    crashes = [f for f in findings if "[CRASH]" in f or "[NO CAREERS]" in f]
    log(f"- **Crashes/empty states:** {len(crashes) if crashes else 'None'}")

    tag_counts = {}
    for f in findings:
        for tag in ["[SEARCH FAIL]", "[NO CAREERS]", "[CRASH]", "[WRONG NUMBER]", "[MISSING]", "[SLOW]", "[BUG]"]:
            if tag in f:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
    if tag_counts:
        log(f"- **Issues:** {', '.join(f'{tag}×{count}' for tag, count in sorted(tag_counts.items()))}")
    else:
        log(f"- **Issues:** None detected")

    browser.close()

    # --- APPEND TO REPORT ---
    report_path = "reports/stress-test-findings.md"
    with open(report_path, "a") as f:
        f.write("\n\n")
        f.write("\n".join(findings))
        f.write("\n")

    print(f"\n\nResults appended to {report_path}")
