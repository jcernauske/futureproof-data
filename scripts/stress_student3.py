"""
Student 3 — The Slider Gauntlet
Home: TX | School: Texas A&M (all 3 builds) | Major: engineering (all 3 builds)
Only slider values change between builds.

Harness fixes from Round 3:
1. Slider selectors: [role='slider'][aria-label='...'] + keyboard arrows
2. Null-stat extraction: per-stat regex handling em-dash
3. Search workaround: search "Texas A", pick College Station campus

Build 1: effort=Working two jobs (0), loans=No loans (0)
Build 2: effort=All-in (4), loans=All loans (4)
Build 3: effort=Balanced (2), loans=Mostly (3)

Same career across all 3 builds so the only variable is effort+loans.
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
    {"effort_idx": 0, "loan_idx": 0},
    {"effort_idx": 4, "loan_idx": 4},
    {"effort_idx": 2, "loan_idx": 3},
]

SKIP_CAREERS = [
    "chief executive", "chief officer", "executive director",
    "postsecondary", "professor",
]

findings = []
builds_data = []


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


# ===== MAIN =====
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    log("## Student #3: The Slider Gauntlet")
    log("- **Persona:** Texas kid, methodical, testing every slider position")
    log("- **Strategy:** Same school + major for ALL builds, only change effort and loan sliders")
    log("  - School: Texas A&M (search \"Texas A\", pick College Station)")
    log("  - Major: engineering")
    log("  - Build 1: effort=Working two jobs (0), loans=No loans (0)")
    log("  - Build 2: effort=All-in (4), loans=All loans (4)")
    log("  - Build 3: effort=Balanced (2), loans=Mostly (3)")
    log("- **Same career across all 3 builds**")

    # --- CREATE PROFILE (TX) ---
    page.goto("http://localhost:5173/profile")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(4000)
    profile_name = page.locator("h1, h2").first.inner_text().strip()
    log(f"\n**Profile:** {profile_name} | Home: TX")
    page.select_option("#home-state", "TX")
    page.locator("text=Let's go").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    target_career_title = None

    for build_idx, config in enumerate(BUILDS_CONFIG):
        build_num = build_idx + 1
        effort_idx = config["effort_idx"]
        loan_idx = config["loan_idx"]

        log(f"\n### Build {build_num} — effort={EFFORT_STOPS[effort_idx]}, loans={LOAN_STOPS[loan_idx]}")

        # Navigate back to SYC if needed
        if build_idx > 0:
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
            page.screenshot(path=f"{SCREENSHOT_DIR}/s3_b{build_num}_stuck.png", full_page=True)
            continue

        # --- SCHOOL SEARCH ---
        search = page.locator("input[placeholder*='Search for your school']")
        search.fill("Texas A")
        try:
            page.locator("[role='option']").first.wait_for(timeout=5000)
        except Exception:
            log("- [SEARCH FAIL] No results for 'Texas A'")
            continue

        options = page.locator("[role='option']").all()
        option_texts = []
        for opt in options:
            try:
                option_texts.append(opt.inner_text().strip())
            except Exception:
                option_texts.append("(unreadable)")

        log(f"  - Search 'Texas A' returned {len(option_texts)} results: {option_texts[:8]}")

        actual_school = ""
        for i, text in enumerate(option_texts):
            if "college station" in text.lower():
                actual_school = text
                options[i].click()
                break
        else:
            for i, text in enumerate(option_texts):
                if "texas a" in text.lower() and "main" in text.lower():
                    actual_school = text
                    options[i].click()
                    break
            else:
                if options:
                    actual_school = option_texts[0]
                    options[0].click()
                    log(f"  - [SEARCH NOTE] Couldn't find College Station, picked: {actual_school}")

        log(f"- School: {actual_school}")
        page.wait_for_timeout(2000)

        # --- MAJOR ---
        major_input = page.locator("input[placeholder*='studying' i]")
        major_input.first.fill("engineering")
        log('- Major: "engineering"')

        # --- WAIT FOR CAREER CARDS ---
        cards = []
        for attempt in range(12):
            page.wait_for_timeout(5000)
            cards = extract_career_cards(page)
            if cards:
                break

        if not cards:
            log("- [NO CAREERS] No career cards after 60s")
            page.screenshot(path=f"{SCREENSHOT_DIR}/s3_b{build_num}_no_careers.png", full_page=True)
            continue

        log(f"- Careers shown: {len(cards)}")

        # --- SET SLIDERS ---
        set_effort(page, effort_idx)
        set_loans(page, loan_idx)
        page.wait_for_timeout(1000)

        # Re-extract cards after slider change (stats update client-side)
        cards = extract_career_cards(page)

        # --- PICK CAREER ---
        if target_career_title is None:
            realistic = [c for c in cards if not any(s in c["title"].lower() for s in SKIP_CAREERS)]
            if not realistic:
                realistic = cards
            realistic.sort(key=lambda c: salary_to_num(c["salary"]))
            best = realistic[len(realistic) // 2]
            target_career_title = best["title"]
            log(f"- **Selected target career for all builds:** {target_career_title}")
        else:
            best = None
            for c in cards:
                if c["title"].lower() == target_career_title.lower():
                    best = c
                    break
            if not best:
                for c in cards:
                    if target_career_title.lower()[:25] in c["title"].lower():
                        best = c
                        break
            if not best:
                log(f"- [WARNING] Career '{target_career_title}' not found, picking closest")
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

        page.screenshot(path=f"{SCREENSHOT_DIR}/s3_b{build_num}_setyourcourse.png", full_page=True)
        log(f"\n**Set Your Course:**\n![SYC]({SCREENSHOT_MD_PREFIX}/s3_b{build_num}_setyourcourse.png)\n")

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
            continue

        build_btn.scroll_into_view_if_needed()
        build_btn.click()
        log("- Building...")

        page.wait_for_timeout(15000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(5000)

        if "/my-build" not in page.url:
            log(f"- [CRASH] Expected /my-build, got {page.url}")
            continue

        # --- REVEAL BOSSES ---
        for btn in page.locator("text=TAP TO REVEAL").all():
            try:
                btn.scroll_into_view_if_needed()
                btn.click()
                page.wait_for_timeout(800)
            except Exception:
                pass
        page.wait_for_timeout(2000)

        page.screenshot(path=f"{SCREENSHOT_DIR}/s3_b{build_num}_results.png", full_page=True)
        log(f"\n**Build Results:**\n![Results]({SCREENSHOT_MD_PREFIX}/s3_b{build_num}_results.png)\n")

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

        log("- **SYC vs Results consistency:**")
        for check in cross_check(syc_data, best, results_data):
            log(f"  - {check}")

        builds_data.append({
            "build_num": build_num,
            "school": actual_school,
            "career": best["title"],
            "card": best,
            "syc": syc_data,
            "results": results_data,
            "effort_idx": effort_idx,
            "effort_label": EFFORT_STOPS[effort_idx],
            "loan_idx": loan_idx,
            "loan_label": LOAN_STOPS[loan_idx],
        })

    # --- CROSS-BUILD COMPARISON ---
    log("\n---\n### Cross-Build Comparison")
    log("")
    log("| # | Effort | Loans | ERN | ROI | RES | GRW | AURA | Cost 4yr | Starting | Debt | Financing | Record |")
    log("|---|--------|-------|-----|-----|-----|-----|------|----------|----------|------|-----------|--------|")
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
        log(f"| {b['build_num']} | {b['effort_label']} | {b['loan_label']} | {ern_s} | {roi_s} | {res_s} | {grw_s} | {aura_s} | ${r.get('published_cost_4yr', '?')} | ${r.get('starting_salary', '?')} | ${r.get('modeled_debt', '?')} | {r.get('financing_pct', '?')}% | {record} |")

    # --- WHAT CHANGED ANALYSIS ---
    log("\n---\n### What Changed Analysis")
    log("")

    if len(builds_data) >= 2:
        all_fields = [
            ("stat_ERN", "ERN"), ("stat_ROI", "ROI"), ("stat_RES", "RES"),
            ("stat_GRW", "GRW"), ("stat_AURA", "AURA"),
            ("published_cost_4yr", "Published cost 4yr"), ("starting_salary", "Starting salary"),
            ("net_price_4yr", "Net price 4yr"), ("modeled_debt", "Modeled debt"),
            ("financing_pct", "Financing %"), ("program_median_debt", "Program median debt"),
            ("boss_AI", "Boss: AI"), ("boss_Loans", "Boss: Loans"),
            ("boss_Market", "Boss: Market"), ("boss_Burnout", "Boss: Burnout"),
            ("boss_Ceiling", "Boss: Ceiling"),
        ]

        changed = []
        unchanged = []
        for key, label in all_fields:
            values = [b["results"].get(key) for b in builds_data]
            val_strs = [str(v) if v is not None else "null" for v in values]
            if len(set(val_strs)) > 1:
                changed.append((label, val_strs))
            else:
                unchanged.append((label, val_strs[0]))

        log("**Fields that CHANGED across builds (B1 → B2 → B3):**")
        for label, vals in changed:
            log(f"- {label}: {' → '.join(vals)}")

        log("")
        log("**Fields that stayed the SAME:**")
        for label, val in unchanged:
            log(f"- {label}: {val}")

        log("")
        log("**Verification checks:**")

        # Does modeled_debt go to $0 at 0% loans?
        b1_debt = builds_data[0]["results"].get("modeled_debt") if builds_data else None
        if b1_debt == "0":
            log("- ✓ modeled_debt = $0 at 0% loans (Build 1)")
        else:
            log(f"- ✗ modeled_debt at 0% loans (Build 1) = ${b1_debt} (expected $0)")

        # Does ERN shift with effort?
        ern_values = [b["results"].get("stat_ERN") for b in builds_data]
        if len(set(str(v) for v in ern_values)) > 1:
            log(f"- ✓ ERN changes with effort: {ern_values}")
        else:
            log(f"- ✗ ERN does NOT change with effort: {ern_values}")

        # Do boss outcomes change?
        for boss in ["AI", "Loans", "Market", "Burnout", "Ceiling"]:
            boss_values = [b["results"].get(f"boss_{boss}") for b in builds_data]
            boss_strs = [str(v) for v in boss_values]
            if len(set(boss_strs)) > 1:
                log(f"- ✓ Boss {boss} changes: {boss_values}")
            else:
                log(f"- • Boss {boss} same across builds: {boss_values[0] if boss_values else '?'}")

        # Does ROI change with debt?
        roi_values = [b["results"].get("stat_ROI") for b in builds_data]
        if len(set(str(v) for v in roi_values)) > 1:
            log(f"- ✓ ROI changes with debt level: {roi_values}")
        else:
            log(f"- • ROI same across builds: {roi_values[0] if roi_values else '?'}")

    browser.close()

    # --- APPEND TO REPORT ---
    report_path = "reports/stress-test-findings.md"
    with open(report_path, "a") as f:
        f.write(f"\n\n---\n\n# Round 4 — {time.strftime('%Y-%m-%d')} — Slider + Edge Case Stress Test\n\n")
        f.write("\n".join(findings))
        f.write("\n")

    print(f"\n\nResults appended to {report_path}")
