"""Recon: what does the page look like when returning to set-your-course after a build?"""
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

    # Do a quick build to get into post-build state
    search = page.locator("input[placeholder*='Search for your school']")
    search.fill("Indiana University")
    page.wait_for_timeout(1500)
    page.locator("[role='option']", has_text="Bloomington").click()
    page.wait_for_timeout(2000)

    major_input = page.locator("input[placeholder*='What are you studying']")
    major_input.fill("business")
    page.wait_for_timeout(4000)

    # Click first career card
    cards = page.locator("button").all()
    for card in cards:
        if "/yr median" in card.inner_text():
            card.click()
            break
    page.wait_for_timeout(1000)

    # Spin build
    page.locator("button", has_text="Spin my build").click()
    page.wait_for_timeout(10000)

    print(f"After build URL: {page.url}")
    page.screenshot(path="/tmp/fp_recon5_after_build.png")

    # Now try to start a NEW build - look for "New Build" button in header
    new_build = page.locator("button", has_text="New Build")
    print(f"'New Build' button count: {new_build.count()}")

    if new_build.count() > 0:
        new_build.click()
        page.wait_for_timeout(2000)
        page.screenshot(path="/tmp/fp_recon5_new_build.png")
        print(f"After 'New Build' URL: {page.url}")

        # Check what inputs are available
        for inp in page.locator("input").all():
            ph = inp.get_attribute("placeholder") or ""
            print(f"  Input: placeholder='{ph}'")

    # Also try navigating directly
    page.goto("http://localhost:5173/set-your-course")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    page.screenshot(path="/tmp/fp_recon5_nav_direct.png")
    print(f"\nDirect nav to /set-your-course:")
    for inp in page.locator("input").all():
        ph = inp.get_attribute("placeholder") or ""
        print(f"  Input: placeholder='{ph}'")

    browser.close()
