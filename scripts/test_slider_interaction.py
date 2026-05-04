"""
Round 3 — Slider interaction diagnostic.
Proves that effort + loan sliders can be driven via Playwright.
Uses ARIA role selectors and keyboard arrows (not input[type='range']).
"""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    # Create a profile and navigate to SYC
    page.goto("http://localhost:5173/profile")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)
    page.select_option("#home-state", "IN")
    page.locator("text=Let's go").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # Pick a school + major to make sliders visible
    search = page.locator("input[placeholder*='Search for your school']")
    search.fill("Indiana University")
    page.locator("[role='option']").first.wait_for(timeout=5000)
    page.locator("[role='option']", has_text="Bloomington").click()
    page.wait_for_timeout(2000)

    major_input = page.locator("input[placeholder*='studying' i]")
    major_input.first.fill("business")
    page.wait_for_timeout(8000)  # wait for career cards

    # ---- SLIDER DIAGNOSTICS ----
    print("\n=== SLIDER DIAGNOSTIC ===\n")

    # Check what input[type='range'] finds
    range_inputs = page.locator("input[type='range']").all()
    print(f"input[type='range'] elements found: {len(range_inputs)}")

    # Check role='slider' elements
    sliders = page.locator("[role='slider']").all()
    print(f"[role='slider'] elements found: {len(sliders)}")

    for i, slider in enumerate(sliders):
        label = slider.get_attribute("aria-label")
        val_now = slider.get_attribute("aria-valuenow")
        val_text = slider.get_attribute("aria-valuetext")
        val_min = slider.get_attribute("aria-valuemin")
        val_max = slider.get_attribute("aria-valuemax")
        print(f"\n  Slider {i + 1}:")
        print(f"    aria-label:     {label}")
        print(f"    aria-valuemin:  {val_min}")
        print(f"    aria-valuemax:  {val_max}")
        print(f"    aria-valuenow:  {val_now}")
        print(f"    aria-valuetext: {val_text}")

    # ---- TEST EFFORT SLIDER ----
    print("\n=== EFFORT SLIDER TEST ===\n")

    effort = page.locator("[role='slider'][aria-label='Effort level']")
    if effort.count() == 0:
        print("ERROR: Effort slider not found!")
    else:
        before = effort.get_attribute("aria-valuetext")
        print(f"Before: {before}")

        # Move to "All-in" (rightmost): ArrowRight from Balanced (index 2) -> focused (3) -> all_in (4)
        effort.focus()
        effort.press("ArrowRight")
        effort.press("ArrowRight")
        page.wait_for_timeout(500)

        after = effort.get_attribute("aria-valuetext")
        print(f"After ArrowRight x2: {after}")

        # Verify the page text updated
        body = page.inner_text("body")
        if "Maximum focus" in body or "All-in" in body:
            print("SUCCESS: Page text reflects 'All-in' / 'Maximum focus'")
        else:
            print("WARNING: Expected 'Maximum focus' or 'All-in' not found in body text")

        # Move to "Working two jobs" (leftmost): ArrowLeft x4 from all_in (4) -> working_hard (0)
        effort.press("ArrowLeft")
        effort.press("ArrowLeft")
        effort.press("ArrowLeft")
        effort.press("ArrowLeft")
        page.wait_for_timeout(500)

        chill = effort.get_attribute("aria-valuetext")
        print(f"After ArrowLeft x4: {chill}")

        if "Working two jobs" in (page.inner_text("body")):
            print("SUCCESS: Page text reflects 'Working two jobs'")

    # ---- TEST LOAN SLIDER ----
    print("\n=== LOAN SLIDER TEST ===\n")

    loan = page.locator("[role='slider'][aria-label='Loan percentage']")
    if loan.count() == 0:
        print("ERROR: Loan slider not found!")
    else:
        before = loan.get_attribute("aria-valuetext")
        print(f"Before: {before}")

        # Move to 100% (rightmost): ArrowRight x2 from Half (index 2) -> Mostly (3) -> All loans (4)
        loan.focus()
        loan.press("ArrowRight")
        loan.press("ArrowRight")
        page.wait_for_timeout(500)

        after = loan.get_attribute("aria-valuetext")
        print(f"After ArrowRight x2: {after}")

        # Check that the loan impact text updated
        body = page.inner_text("body")
        if "100%" in body and ("full difficulty" in body or "financing 100%" in body):
            print("SUCCESS: Loan impact text updated to 100%")
        else:
            print("INFO: Looking for '100%' in body...")
            # Find the relevant chunk
            for line in body.split("\n"):
                if "financ" in line.lower() or "loan" in line.lower() or "100%" in line:
                    print(f"  Found: {line.strip()[:80]}")

        # Move to 0% (leftmost): ArrowLeft x4
        loan.press("ArrowLeft")
        loan.press("ArrowLeft")
        loan.press("ArrowLeft")
        loan.press("ArrowLeft")
        page.wait_for_timeout(500)

        zero = loan.get_attribute("aria-valuetext")
        print(f"After ArrowLeft x4: {zero}")

        body = page.inner_text("body")
        if "no debt" in body.lower() or "auto-win" in body.lower():
            print("SUCCESS: Loan impact text updated to no-debt/auto-win")

    # ---- COMBINED: Set to "grind" + 75% loans, verify SYC financials ----
    print("\n=== COMBINED: EFFORT=All-in + LOANS=75% ===\n")

    # Reset effort to all_in
    effort = page.locator("[role='slider'][aria-label='Effort level']")
    effort.focus()
    # From working_hard (0) -> all_in (4): ArrowRight x4
    for _ in range(4):
        effort.press("ArrowRight")
    page.wait_for_timeout(300)
    print(f"Effort: {effort.get_attribute('aria-valuetext')}")

    # Set loans to 75%
    loan = page.locator("[role='slider'][aria-label='Loan percentage']")
    loan.focus()
    # From 0 (index 0) -> 75 (index 3): ArrowRight x3
    for _ in range(3):
        loan.press("ArrowRight")
    page.wait_for_timeout(500)
    print(f"Loans: {loan.get_attribute('aria-valuetext')}")

    body = page.inner_text("body")
    for line in body.split("\n"):
        stripped = line.strip()
        if any(kw in stripped.lower() for kw in ["financing", "in loans", "maximum", "strong focus", "all-in"]):
            if len(stripped) > 5 and len(stripped) < 120:
                print(f"  Page text: {stripped}")

    print("\n=== DONE ===")

    browser.close()
