"""Test: can we do multiple builds under one profile by navigating directly to /set-your-course?"""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    # Create profile ONCE
    page.goto("http://localhost:5173/profile")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)
    profile_name = page.locator("h1, h2").first.inner_text().strip()
    print(f"Profile: {profile_name}")
    page.select_option("#home-state", "IN")
    page.locator("text=Let's go").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    print(f"After Let's go: {page.url}")

    # --- BUILD 1 ---
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

    # --- Navigate directly to /set-your-course (no profile reset) ---
    page.goto("http://localhost:5173/set-your-course")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    print(f"After direct nav to /set-your-course: {page.url}")

    # Check if school search is available (means profile is preserved)
    search2 = page.locator("input[placeholder*='Search for your school']")
    print(f"School search input available: {search2.count()}")

    if search2.count() > 0:
        # --- BUILD 2 ---
        search2.fill("Purdue University")
        page.wait_for_timeout(1500)
        page.locator("[role='option']", has_text="Main Campus").click()
        page.wait_for_timeout(2000)
        page.locator("input[placeholder*='studying' i]").fill("business")
        for _ in range(6):
            page.wait_for_timeout(5000)
            cards = [b for b in page.locator("button").all() if "/yr median" in b.inner_text()]
            if cards:
                break
        if cards:
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
            print(f"Build 2 done: {page.url}")

            # Check builds menu
            page.goto("http://localhost:5173/builds")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)
            body = page.inner_text("body")
            print(f"\nBuilds menu URL: {page.url}")
            # Count build cards
            if "Indiana" in body and "Purdue" in body:
                print("BOTH builds visible in menu!")
            elif "Indiana" in body:
                print("Only IU build visible")
            elif "Purdue" in body:
                print("Only Purdue build visible")
            else:
                print("Neither build visible")
            page.screenshot(path="/tmp/fp_recon_sameprofile_menu.png", full_page=True)
    else:
        print("Profile was lost — redirected away from set-your-course")
        page.screenshot(path="/tmp/fp_recon_sameprofile_fail.png")

    browser.close()
