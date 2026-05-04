"""
Student 1 — The Indiana Kid (with compare)
Home: IN | Schools: IU Bloomington, Purdue, Ball State, Indiana State
Major: "business" | Career: realistic mid-range | Effort: balanced | Loans: 50%

All 4 builds under ONE profile so they appear together in the builds menu
and can be compared. Uses "Start over" to return to set-your-course between builds.

Cross-screen consistency: every data point captured from Set Your Course,
Build Results, and Compare — checked for mismatches.
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

SCHOOLS = [
    ("Indiana University", "Bloomington"),
    ("Purdue University", "Main Campus"),
    ("Ball State", "Ball State"),
    ("Indiana State", "Indiana State"),
]

SKIP_CAREERS = [
    "chief executive", "chief officer", "executive director",
    "postsecondary", "professor",
]

findings = []
builds = []


def log(msg):
    findings.append(msg)
    print(msg)


def salary_to_num(s):
    return int(s.replace("$", "").replace(",", ""))


def extract_career_cards(page):
    cards = []
    for btn in page.locator("button").all():
        text = btn.inner_text()
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
                    and line not in ("ERN", "ROI", "RES", "GRW", "AURA", "🧭", "📊", "📚",
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
    m = re.search(r"financing\s+\d+%\s+of\s+\$([\d,]+)", text)
    if m:
        data["published_cost_4yr"] = m.group(1).replace(",", "")
    m = re.search(r"At\s+\d+%:\s+\$([\d,]+)\s+in loans", text)
    if m:
        data["modeled_debt"] = m.group(1).replace(",", "")
    m = re.search(r"\$([\d,]+)/yr\s.*?=\s+\$([\d,]+)\s+total", text)
    if m:
        data["annual_cost"] = m.group(1).replace(",", "")
        data["total_cost_calc"] = m.group(2).replace(",", "")
    return data


def extract_build_results(page):
    text = page.inner_text("body")
    data = {}

    path_block = re.search(
        r'YOUR PATH\n.*?ERN\n(\d+)\nROI\n(\d+)\nRES\n(\d+)\nGRW\n(\d+)\nAURA\n(\d+)',
        text, re.DOTALL)
    if path_block:
        for i, stat in enumerate(["ERN", "ROI", "RES", "GRW", "AURA"]):
            data[f"stat_{stat}"] = int(path_block.group(i + 1))

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
        if cv is not None and rv is not None:
            if cv != rv:
                checks.append(f"[WRONG NUMBER] {stat}: card={cv} vs Results={rv}")
            else:
                checks.append(f"{stat} consistent: {rv}")
    return checks


def do_build(page, school_search, school_match, major, build_num, is_first):
    log(f"\n### Build {build_num}")

    if is_first:
        # Already on /set-your-course from profile flow
        pass
    elif "/my-build" in page.url:
        # On results page — use "Start over"
        start_over = page.locator("text=Start over")
        if start_over.count() > 0:
            start_over.first.click()
            page.wait_for_timeout(3000)
        yes_btn = page.locator("text=Yes, start over")
        if yes_btn.count() > 0:
            yes_btn.click()
            page.wait_for_timeout(2000)
    elif "/set-your-course" in page.url:
        # Still on set-your-course from a failed build — clear school and retry
        clear_btn = page.locator("button", has_text="✕")
        if clear_btn.count() > 0:
            clear_btn.first.click()
            page.wait_for_timeout(1000)
    else:
        # Unknown state — try clicking "New Build" in header
        new_build = page.locator("button", has_text="New Build")
        if new_build.count() > 0:
            new_build.click()
            page.wait_for_timeout(3000)

    # Wait for school search to appear
    try:
        page.locator("input[placeholder*='Search for your school']").wait_for(timeout=10000)
    except Exception:
        log(f"- [CRASH] School search not found. URL: {page.url}")
        page.screenshot(path=f"{SCREENSHOT_DIR}/s1_b{build_num}_stuck.png", full_page=True)
        return None

    # --- SCHOOL SEARCH ---
    search = page.locator("input[placeholder*='Search for your school']")
    search.fill(school_search)
    try:
        page.locator("[role='option']").first.wait_for(timeout=5000)
    except Exception:
        search.fill(school_search.split()[0])
        page.wait_for_timeout(2000)

    options = page.locator("[role='option']").all()
    actual_school = ""
    for opt in options:
        if school_match.lower() in opt.inner_text().lower():
            actual_school = opt.inner_text().strip()
            opt.click()
            break
    else:
        if options:
            actual_school = options[0].inner_text().strip()
            options[0].click()
            log(f"- [SEARCH FAIL] Wanted '{school_match}', got: {actual_school}")
        else:
            log(f"- [SEARCH FAIL] No results for '{school_search}'")
            return None

    log(f"- School: {actual_school}")
    page.wait_for_timeout(2000)

    # --- MAJOR ---
    major_input = page.locator("input[placeholder*='studying' i]")
    major_input.first.fill(major)
    log(f"- Major: \"{major}\"")

    cards = []
    for attempt in range(10):
        page.wait_for_timeout(5000)
        cards = extract_career_cards(page)
        if cards:
            break

    if not cards:
        no_path = f"{SCREENSHOT_DIR}/s1_b{build_num}_no_careers.png"
        page.screenshot(path=no_path, full_page=True)
        log(f"- [NO CAREERS] No career cards after 30s")
        log(f"\n![No careers]({SCREENSHOT_MD_PREFIX}/s1_b{build_num}_no_careers.png)\n")
        return None

    log(f"- Careers shown: {len(cards)}")

    # --- CAREER SELECTION ---
    realistic = [c for c in cards if not any(s in c["title"].lower() for s in SKIP_CAREERS)]
    if not realistic:
        realistic = cards
    realistic.sort(key=lambda c: salary_to_num(c["salary"]))
    best = realistic[len(realistic) // 2]
    best["element"].click()
    page.wait_for_timeout(1000)

    log(f"- **Career:** {best['title']} ({best['salary']}/yr)")
    log(f"  - Card stats: ERN={best['stats'].get('ERN','?')} ROI={best['stats'].get('ROI','?')} RES={best['stats'].get('RES','?')} GRW={best['stats'].get('GRW','?')} AURA={best['stats'].get('AURA','?')}")

    # --- SYC FINANCIALS ---
    syc_data = extract_syc_financials(page)
    if syc_data:
        log(f"  - SYC financials: cost_4yr=${syc_data.get('published_cost_4yr','?')} debt=${syc_data.get('modeled_debt','?')}")

    syc_path = f"{SCREENSHOT_DIR}/s1_b{build_num}_setyourcourse.png"
    page.screenshot(path=syc_path, full_page=True)
    log(f"\n**Set Your Course:**\n![SYC]({SCREENSHOT_MD_PREFIX}/s1_b{build_num}_setyourcourse.png)\n")

    # --- BUILD ---
    build_btn = None
    for b in page.locator("button").all():
        if "spec my build" in b.inner_text().lower():
            build_btn = b
            break
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

    results_path = f"{SCREENSHOT_DIR}/s1_b{build_num}_results.png"
    page.screenshot(path=results_path, full_page=True)
    log(f"\n**Build Results:**\n![Results]({SCREENSHOT_MD_PREFIX}/s1_b{build_num}_results.png)\n")

    # --- EXTRACT ---
    results_data = extract_build_results(page)

    log(f"- **Results data:**")
    log(f"  - Starting salary: ${results_data.get('starting_salary','?')} | Median: ${results_data.get('median_salary','?')}")
    log(f"  - Cost 4yr: ${results_data.get('published_cost_4yr','?')} | Net price: ${results_data.get('net_price_4yr','?')}")
    log(f"  - Modeled debt: ${results_data.get('modeled_debt','?')} | Program median debt: ${results_data.get('program_median_debt','?')}")
    log(f"  - Financing: {results_data.get('financing_pct','?')}%")

    stat_str = " ".join(f"{s}={results_data.get(f'stat_{s}', '?')}" for s in ["ERN", "ROI", "RES", "GRW", "AURA"])
    log(f"  - Pentagon: {stat_str}")

    boss_str = " | ".join(f"{b}={results_data.get(f'boss_{b}', '?')}" for b in ["AI", "Loans", "Market", "Burnout", "Ceiling"])
    log(f"  - Bosses: {boss_str}")

    if results_data.get("wins") is not None:
        log(f"  - Record: {results_data['wins']}W / {results_data.get('standoffs',0)}S / {results_data.get('defeats',0)}D")

    # --- CONSISTENCY ---
    log(f"- **SYC vs Results consistency:**")
    for check in cross_check(syc_data, best, results_data):
        log(f"  - {check}")

    builds.append({
        "build_num": build_num,
        "school": actual_school,
        "major": major,
        "career": best["title"],
        "card": best,
        "syc": syc_data,
        "results": results_data,
    })
    return True


# ===== MAIN =====
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    log("## Student #1: The Indiana Kid")
    log("- **Persona:** 16-year-old from Indiana, checking in-state schools")
    log("- **Vibe:** I live here, my parents went here, let's see what business gets me")
    log("- **Strategy:** 4 Indiana schools, same major (business), realistic mid-range career")
    log("- **All builds under one profile** so they can be compared")

    # --- CREATE PROFILE ONCE ---
    page.goto("http://localhost:5173/profile")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(4000)
    profile_name = page.locator("h1, h2").first.inner_text().strip()
    log(f"\n**Profile:** {profile_name} | Home: IN")
    page.select_option("#home-state", "IN")
    page.locator("text=Let's go").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # --- 4 BUILDS ---
    for i, (search_term, match_text) in enumerate(SCHOOLS, 1):
        try:
            do_build(page, search_term, match_text, "business", i, is_first=(i == 1))
        except Exception as e:
            log(f"\n### Build {i}\n- [CRASH] {e}")

    # --- BUILDS MENU (use header button, not page.goto, to preserve Zustand state) ---
    log("\n---\n### Builds Menu")
    my_builds_btn = page.locator("button", has_text="My Builds")
    if my_builds_btn.count() > 0:
        my_builds_btn.first.click()
        page.wait_for_timeout(3000)
    else:
        log("- [CRASH] No 'My Builds' button in header")

    menu_path = f"{SCREENSHOT_DIR}/s1_builds_menu.png"
    page.screenshot(path=menu_path, full_page=True)
    log(f"\n![Builds Menu]({SCREENSHOT_MD_PREFIX}/s1_builds_menu.png)\n")

    menu_text = page.inner_text("body")
    for b in builds:
        school_short = b["school"].split("-")[0].strip().split(",")[0].strip()
        found = school_short.lower() in menu_text.lower() or b["career"].lower()[:20] in menu_text.lower()
        log(f"- Build {b['build_num']} ({b['school'][:30]}): {'visible' if found else '[STALE] NOT FOUND'}")

    # Cross-check builds-menu API data against build results
    log("\n**Builds Menu API cross-check:**")
    try:
        profile_encoded = urllib.parse.quote(profile_name)
        req = urllib.request.Request(f"{API_BASE}/builds?profile_name={profile_encoded}")
        with urllib.request.urlopen(req) as resp:
            api_builds_list = json.loads(resp.read())["builds"]
        log(f"- API returned {len(api_builds_list)} builds")

        for ab in api_builds_list:
            matched = None
            for b in builds:
                if b["school"].lower()[:15] in ab["school_name"].lower() or ab["school_name"].lower()[:15] in b["school"].lower():
                    matched = b
                    break
            if not matched:
                log(f"- [STALE] API build '{ab['school_name']}' not matched")
                continue
            r = matched.get("results", {})
            mismatches = []
            for stat in ["ern", "roi", "res", "grw", "aura"]:
                api_val = ab.get(stat)
                page_val = r.get(f"stat_{stat.upper()}")
                if api_val is not None and page_val is not None and int(api_val) != int(page_val):
                    mismatches.append(f"{stat.upper()}: menu={api_val} vs results={page_val}")
            record_api = f"{ab.get('wins','?')}W-{ab.get('draws','?')}S-{ab.get('losses','?')}D"
            record_page = f"{r.get('wins','?')}W-{r.get('standoffs','?')}S-{r.get('defeats','?')}D"
            if mismatches:
                log(f"  - Build {matched['build_num']} ({ab['school_name'][:25]}): [WRONG NUMBER] {', '.join(mismatches)}")
            else:
                log(f"  - Build {matched['build_num']} ({ab['school_name'][:25]}): stats consistent | Record: API={record_api} Page={record_page}")
    except Exception as e:
        log(f"- [CRASH] Builds menu API cross-check failed: {e}")

    # --- COMPARE ---
    log("\n---\n### Compare: Build 1 vs Build 2")

    # Click "Compare" button in header to enter select mode
    compare_header = page.locator("button", has_text="Compare")
    if compare_header.count() > 0:
        compare_header.first.click()
        page.wait_for_timeout(2000)
        page.screenshot(path=f"{SCREENSHOT_DIR}/s1_compare_select.png", full_page=True)
        log(f"\n**Select mode:**\n![Select]({SCREENSHOT_MD_PREFIX}/s1_compare_select.png)\n")

        log(f"- Select mode URL: {page.url}")

        # Select the first two DISTINCT builds from our Student 1 session.
        # Build cards show school name + career. Match against our builds list.
        selected_schools = set()
        clicked = 0
        all_cards = page.locator("button, [role='button'], li").all()
        for card in all_cards:
            if clicked >= 2:
                break
            try:
                text = card.inner_text().strip()
            except Exception:
                continue
            if len(text) < 20:
                continue
            for b in builds:
                school_short = b["school"].split("-")[0].strip()[:12].lower()
                if school_short in text.lower() and school_short not in selected_schools:
                    try:
                        card.click()
                        clicked += 1
                        selected_schools.add(school_short)
                        page.wait_for_timeout(500)
                        log(f"  - Selected: {text[:60]}")
                    except Exception:
                        pass
                    break

        log(f"- Selected {clicked} distinct builds")

        if clicked >= 2:
            page.wait_for_timeout(1000)
            page.screenshot(path=f"{SCREENSHOT_DIR}/s1_compare_selected.png", full_page=True)
            log(f"\n**Builds selected:**\n![Selected]({SCREENSHOT_MD_PREFIX}/s1_compare_selected.png)\n")

            # Find the action button — "Compare (2)" or similar
            action_clicked = False
            for btn in page.locator("button").all():
                try:
                    text = btn.inner_text().strip()
                except Exception:
                    continue
                if "compare" in text.lower() and ("2" in text or "go" in text.lower() or "selected" in text.lower()):
                    btn.click()
                    page.wait_for_timeout(8000)
                    log(f"  - Clicked: '{text}'")
                    action_clicked = True
                    break

            if not action_clicked:
                log("  - [CRASH] Couldn't find compare action button")

        # Screenshot the compare view
        page.wait_for_timeout(2000)
        compare_path = f"{SCREENSHOT_DIR}/s1_compare.png"
        page.screenshot(path=compare_path, full_page=True)
        log(f"\n**Compare View:**\n![Compare]({SCREENSHOT_MD_PREFIX}/s1_compare.png)\n")

    else:
        log("- [CRASH] No Compare button found")

    # --- API-LEVEL COMPARE CROSS-CHECK ---
    log("\n---\n### Compare vs Build Results (API cross-check)")
    log("")
    try:
        profile_encoded = urllib.parse.quote(profile_name)
        req = urllib.request.Request(f"{API_BASE}/builds?profile_name={profile_encoded}")
        with urllib.request.urlopen(req) as resp:
            api_builds = json.loads(resp.read())["builds"]
        log(f"- API returned {len(api_builds)} builds for profile '{profile_name}'")

        # Deduplicate by school name (double-submit bug creates pairs)
        seen_schools = set()
        deduped = []
        for ab in api_builds:
            if ab["school_name"] not in seen_schools:
                seen_schools.add(ab["school_name"])
                deduped.append(ab)
        if len(deduped) < len(api_builds):
            log(f"- [BUG] {len(api_builds) - len(deduped)} duplicate builds detected (double-submission bug)")
        api_builds = deduped

        if len(api_builds) >= 2:
            build_ids = [b["build_id"] for b in api_builds]
            compare_req = urllib.request.Request(
                f"{API_BASE}/builds/compare",
                data=json.dumps({"build_ids": build_ids}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(compare_req) as resp:
                compare_data = json.loads(resp.read())

            compare_builds_api = compare_data["builds"]
            compare_stats = compare_data["stats"]
            compare_bosses = compare_data["bosses"]

            stat_lookup = {}
            for row in compare_stats:
                stat_lookup[row["label"]] = row["values"]

            boss_lookup = {}
            for row in compare_bosses:
                boss_lookup[row["boss_id"]] = row["values"]

            log(f"- Compare API returned {len(compare_builds_api)} builds, {len(compare_stats)} stat rows, {len(compare_bosses)} boss rows")
            log("")

            for ci, cb in enumerate(compare_builds_api):
                matched_build = None
                for b in builds:
                    if b["school"].lower()[:15] in cb["school_name"].lower() or cb["school_name"].lower()[:15] in b["school"].lower():
                        matched_build = b
                        break
                if not matched_build:
                    log(f"- [STALE] Compare build '{cb['school_name']}' not matched to any local build")
                    continue

                r = matched_build.get("results", {})
                log(f"#### {cb['school_name']} (Build {matched_build['build_num']})")
                log("")
                mismatches = 0

                checks = [
                    ("published_cost_4yr", cb.get("published_cost_4yr"), r.get("published_cost_4yr")),
                    ("modeled_total_debt", cb.get("modeled_total_debt"), r.get("modeled_debt")),
                    ("median_annual_wage", cb.get("median_annual_wage"), r.get("median_salary")),
                    ("net_price_annual×4", (cb["net_price_annual"] * 4) if cb.get("net_price_annual") else None, r.get("net_price_4yr")),
                ]
                for label, api_val, page_val in checks:
                    if api_val is None and page_val is None:
                        log(f"  - {label}: both null")
                        continue
                    api_str = str(int(api_val)) if api_val is not None else "null"
                    page_str = str(page_val) if page_val is not None else "null"
                    if api_str == page_str:
                        log(f"  - {label} consistent: ${api_str}")
                    else:
                        log(f"  - [WRONG NUMBER] {label}: compare API={api_str} vs build page={page_str}")
                        mismatches += 1

                for stat in ["ERN", "ROI", "RES", "GRW", "AURA"]:
                    api_val = stat_lookup.get(stat, [None] * (ci + 1))[ci]
                    page_val = r.get(f"stat_{stat}")
                    if api_val is not None and page_val is not None:
                        if int(api_val) == int(page_val):
                            log(f"  - {stat} consistent: {int(api_val)}")
                        else:
                            log(f"  - [WRONG NUMBER] {stat}: compare API={api_val} vs build page={page_val}")
                            mismatches += 1
                    else:
                        log(f"  - {stat}: API={api_val} page={page_val}")

                boss_map = {"ai": "AI", "loans": "Loans", "market": "Market", "burnout": "Burnout", "ceiling": "Ceiling"}
                for boss_id, boss_key in boss_map.items():
                    api_vals = boss_lookup.get(boss_id, [])
                    api_outcome = api_vals[ci] if ci < len(api_vals) else None
                    page_outcome = r.get(f"boss_{boss_key}")
                    if api_outcome and page_outcome:
                        api_norm = {"WIN": "VICTORY", "DRAW": "STANDOFF", "LOSE": "DEFEATED"}.get(api_outcome, api_outcome)
                        if api_norm == page_outcome:
                            log(f"  - Boss {boss_key} consistent: {page_outcome}")
                        else:
                            log(f"  - [WRONG NUMBER] Boss {boss_key}: compare API={api_outcome} vs build page={page_outcome}")
                            mismatches += 1
                    else:
                        log(f"  - Boss {boss_key}: API={api_outcome} page={page_outcome}")

                if mismatches == 0:
                    log(f"  - **All checks passed**")
                else:
                    log(f"  - **{mismatches} mismatch(es) found**")
                log("")

    except Exception as e:
        log(f"- [CRASH] API compare cross-check failed: {e}")

    # --- CROSS-BUILD TABLE ---
    log("\n---\n### Cross-Build Comparison")
    log("")
    log("| # | School | Career | ERN | ROI | RES | GRW | AURA | Cost 4yr | Starting | Debt | Record |")
    log("|---|--------|--------|-----|-----|-----|-----|------|----------|----------|------|--------|")
    for b in builds:
        r = b.get("results", {})
        record = f"{r.get('wins','?')}W-{r.get('standoffs','?')}S-{r.get('defeats','?')}D"
        log(f"| {b['build_num']} | {b['school'][:25]} | {b['career'][:25]} | {r.get('stat_ERN','?')} | {r.get('stat_ROI','?')} | {r.get('stat_RES','?')} | {r.get('stat_GRW','?')} | {r.get('stat_AURA','?')} | ${r.get('published_cost_4yr','?')} | ${r.get('starting_salary','?')} | ${r.get('modeled_debt','?')} | {record} |")

    browser.close()

    # --- WRITE REPORT ---
    report_path = "reports/stress-test-findings.md"
    with open(report_path, "w") as f:
        f.write(f"# FutureProof Stress Test Log\n")
        f.write(f"- **Started:** {time.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"- **Tester:** Claude Code via Playwright\n")
        f.write(f"- **App:** http://localhost:5173\n\n---\n\n")
        f.write("\n".join(findings))
        f.write("\n")

    print(f"\n\nReport written to {report_path}")
