"""Recon: what does clicking 'New Build' from results do? Does it keep the same profile?"""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    # Profile
    page.goto("http://localhost:5173/profile")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)
    profile_name = page.locator("h1, h2").first.inner_text().strip()
    print(f"Profile created: {profile_name}")
    page.select_option("#home-state", "IN")
    page.locator("text=Let's go").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # Quick build
    page.locator("input[placeholder*='Search for your school']").fill("Indiana University")
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
    print(f"Build 1 done, URL: {page.url}")

    # Now click "New Build" in header
    new_build_btn = page.locator("button", has_text="New Build")
    print(f"'New Build' button visible: {new_build_btn.count()}")
    if new_build_btn.count() > 0:
        new_build_btn.click()
        page.wait_for_timeout(2000)
        print(f"After 'New Build' URL: {page.url}")

        # Check if profile is preserved
        body = page.inner_text("body")
        if profile_name.split()[-1] in body:
            print(f"Profile name still visible: YES")
        else:
            print(f"Profile name NOT visible — new profile created?")

        # Check for school search input
        search = page.locator("input[placeholder*='Search for your school']")
        print(f"School search input: {search.count()}")

        page.screenshot(path="/tmp/fp_recon_newbuild.png", full_page=True)

    browser.close()
