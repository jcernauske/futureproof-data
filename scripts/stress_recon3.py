"""Recon phase 3: search school, type major, inspect career cards."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    # Complete profile
    page.goto("http://localhost:5173/profile")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)
    page.select_option("#home-state", "IN")
    page.locator("text=Let's go").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # Search for school
    search = page.locator("input[placeholder*='Search for your school']")
    search.fill("Indiana University")
    page.wait_for_timeout(2000)
    page.screenshot(path="/tmp/fp_recon3_school_results.png", full_page=True)

    # See what dropdown options appeared
    print("=== SCHOOL SEARCH RESULTS ===")
    # Look for listbox items, dropdown items, or any results
    for sel in ["[role='option']", "[role='listbox'] li", ".search-result", "[data-testid]"]:
        items = page.locator(sel).all()
        if items:
            print(f"Found {len(items)} items with selector '{sel}':")
            for item in items[:5]:
                print(f"  {item.inner_text().strip()[:80]}")

    # Also try generic approach
    all_text = page.locator("ul li, [role='option'], [role='listbox'] > *").all()
    if all_text:
        print(f"\nGeneric list items: {len(all_text)}")
        for item in all_text[:8]:
            t = item.inner_text().strip()[:80]
            if t:
                print(f"  {t}")

    browser.close()
