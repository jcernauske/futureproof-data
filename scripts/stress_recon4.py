"""Recon phase 4: select school, type major, see career cards and effort/loan controls."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    # Complete profile
    page.goto("http://localhost:5173/profile")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)
    profile_name = page.locator("h1, h2").first.inner_text().strip()
    print(f"Profile: {profile_name}")
    page.select_option("#home-state", "IN")
    page.locator("text=Let's go").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # Search and select school
    search = page.locator("input[placeholder*='Search for your school']")
    search.fill("Indiana University")
    page.wait_for_timeout(1500)
    page.locator("[role='option']", has_text="Indiana University-Bloomington").click()
    page.wait_for_timeout(2000)
    page.screenshot(path="/tmp/fp_recon4_school_selected.png", full_page=True)

    print("\n=== AFTER SCHOOL SELECTION ===")
    print("Inputs:")
    for inp in page.locator("input").all():
        ph = inp.get_attribute("placeholder") or ""
        val = inp.input_value()
        print(f"  placeholder='{ph}' value='{val}'")

    # Look for a major/field input
    major_input = page.locator("input[placeholder*='major' i], input[placeholder*='field' i], input[placeholder*='study' i], input[placeholder*='what' i]")
    print(f"\nMajor-related inputs: {major_input.count()}")
    if major_input.count() == 0:
        # Maybe it's a different element
        print("Checking textareas and other inputs...")
        for inp in page.locator("input, textarea").all():
            ph = inp.get_attribute("placeholder") or ""
            print(f"  {inp.evaluate('el => el.tagName')} placeholder='{ph}'")

    # Type the major
    if major_input.count() > 0:
        major_input.first.fill("business")
    else:
        # Try filling the second input on the page
        all_inputs = page.locator("input").all()
        if len(all_inputs) > 1:
            all_inputs[1].fill("business")
            print(f"Filled second input with 'business'")

    page.wait_for_timeout(3000)
    page.screenshot(path="/tmp/fp_recon4_major_typed.png", full_page=True)

    # Check for career cards or CIP resolution
    print("\n=== AFTER TYPING MAJOR ===")
    # Look for career-related elements
    for sel in ["[data-testid*='career']", ".career-card", "[role='button']", "button"]:
        items = page.locator(sel).all()
        relevant = [i for i in items if any(kw in i.inner_text().lower() for kw in ["career", "salary", "wage", "$", "analyst", "manager", "engineer"])]
        if relevant:
            print(f"Career-like elements ({sel}):")
            for item in relevant[:5]:
                print(f"  {item.inner_text().strip()[:100]}")

    browser.close()
