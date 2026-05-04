"""Recon phase 2: complete profile flow, then inspect Set Your Course."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    # Start at profile
    page.goto("http://localhost:5173/profile")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    # Read the generated profile
    heading = page.locator("h1, h2").first.inner_text()
    print(f"Profile name: {heading}")

    # Select home state = IN
    page.select_option("#home-state", "IN")
    page.wait_for_timeout(500)
    page.screenshot(path="/tmp/fp_recon2_profile_with_state.png")

    # Click "Let's go"
    page.locator("text=Let's go").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    page.screenshot(path="/tmp/fp_recon2_setyourcourse.png", full_page=True)

    print(f"\nURL after Let's go: {page.url}")
    print("\n=== SET YOUR COURSE ===")
    print("Inputs:")
    for inp in page.locator("input").all():
        attrs = {
            "placeholder": inp.get_attribute("placeholder"),
            "type": inp.get_attribute("type"),
            "id": inp.get_attribute("id"),
            "role": inp.get_attribute("role"),
        }
        print(f"  {attrs}")

    print("\nButtons:")
    for btn in page.locator("button").all():
        text = btn.inner_text().strip()[:50]
        if text:
            print(f"  [{text}]")

    # Look for school search
    print("\nSearching for school search input...")
    search = page.locator("input[placeholder*='school' i], input[placeholder*='search' i], input[placeholder*='college' i], input[placeholder*='university' i]")
    print(f"  Found {search.count()} school-related inputs")

    browser.close()
