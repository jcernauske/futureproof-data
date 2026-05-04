"""Reconnaissance: screenshot the landing page and profile screen to discover selectors."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    # Landing page
    page.goto("http://localhost:5173")
    page.wait_for_load_state("networkidle")
    page.screenshot(path="/tmp/fp_recon_landing.png", full_page=True)
    print("=== LANDING PAGE LINKS ===")
    for link in page.locator("a").all():
        href = link.get_attribute("href") or ""
        text = link.inner_text().strip()[:60]
        if text:
            print(f"  [{text}] -> {href}")

    # Navigate to profile
    page.goto("http://localhost:5173/profile")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)  # wait for profile generation
    page.screenshot(path="/tmp/fp_recon_profile.png", full_page=True)
    print("\n=== PROFILE PAGE ===")
    print("Buttons:", [b.inner_text().strip() for b in page.locator("button").all()])
    print("Selects:", [s.get_attribute("id") or s.get_attribute("name") or "unnamed" for s in page.locator("select").all()])
    # Check for state dropdown
    for el in page.locator("select").all():
        options = el.locator("option").all()
        if len(options) > 40:
            print(f"  State dropdown found with {len(options)} options")

    # Navigate to set-your-course
    page.goto("http://localhost:5173/set-your-course")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    page.screenshot(path="/tmp/fp_recon_setyourcourse.png", full_page=True)
    print("\n=== SET YOUR COURSE PAGE ===")
    print("Inputs:", [(i.get_attribute("placeholder") or i.get_attribute("id") or "unnamed") for i in page.locator("input").all()])
    print("Buttons:", [b.inner_text().strip()[:40] for b in page.locator("button").all()])

    browser.close()
    print("\nScreenshots saved to /tmp/fp_recon_*.png")
