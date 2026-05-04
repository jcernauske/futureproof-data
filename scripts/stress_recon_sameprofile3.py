"""Test: click Start over -> Yes, start over -> see what happens."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    # Create profile + Build 1 (quick)
    page.goto("http://localhost:5173/profile")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)
    profile_name = page.locator("h1, h2").first.inner_text().strip()
    print(f"Profile: {profile_name}")
    page.select_option("#home-state", "IN")
    page.locator("text=Let's go").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    search = page.locator("input[placeholder*='Search for your school']")
    search.fill("Indiana University")
    page.wait_for_timeout(1500)
    page.locator("[role='option']", has_text="Bloomington").click()
    page.wait_for_timeout(2000)
    page.locator("input[placeholder*='studying' i]").fill("business")
    for _ in range(6):
        page.wait_for_timeout(5000)
        cards = [b for b in page.locator("button").all() if "/yr median" in b.inner_text()]
        if cards:
            break
    cards[len(cards)//2].click()
    page.wait_for_timeout(1000)
    for b in page.locator("button").all():
        if "spec my build" in b.inner_text().lower():
            b.scroll_into_view_if_needed()
            b.click()
            break
    page.wait_for_timeout(15000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)
    print(f"Build 1 done: {page.url}")

    # Click "Start over"
    page.locator("text=Start over").first.click()
    page.wait_for_timeout(1000)
    page.screenshot(path="/tmp/fp_recon_startover1.png")
    print(f"After Start over: {page.url}")

    # Check for confirmation dialog
    yes_btn = page.locator("text=Yes, start over")
    print(f"'Yes, start over' visible: {yes_btn.count()}")
    if yes_btn.count() > 0:
        yes_btn.click()
        page.wait_for_timeout(2000)
        page.screenshot(path="/tmp/fp_recon_startover2.png")
        print(f"After 'Yes': {page.url}")

        # Now check the page
        all_inputs = page.locator("input").all()
        print(f"Inputs on page: {len(all_inputs)}")
        for inp in all_inputs:
            ph = inp.get_attribute("placeholder") or ""
            print(f"  placeholder='{ph}'")

        # Check if profile name still exists in page
        body = page.inner_text("body")
        # The profile name might be in the header
        for word in profile_name.split():
            if word in body:
                print(f"Profile word '{word}' found in page text")

    browser.close()
