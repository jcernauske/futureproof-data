"""Debug: click a career card, then inspect what buttons exist (especially the build button)."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    # Profile
    page.goto("http://localhost:5173/profile")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)
    page.select_option("#home-state", "IN")
    page.locator("text=Let's go").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # School
    search = page.locator("input[placeholder*='Search for your school']")
    search.fill("Indiana University")
    page.wait_for_timeout(1500)
    page.locator("[role='option']", has_text="Bloomington").click()
    page.wait_for_timeout(2000)

    # Major
    page.locator("input[placeholder*='studying' i]").fill("business")
    page.wait_for_timeout(5000)

    # Find and click first career card
    for btn in page.locator("button").all():
        text = btn.inner_text()
        if "/yr median" in text and "ERN" in text:
            print(f"Clicking career: {text.split(chr(10))[0]}")
            btn.click()
            break

    page.wait_for_timeout(2000)

    # Now check ALL buttons on page
    print("\n=== ALL BUTTONS AFTER CAREER CLICK ===")
    for btn in page.locator("button").all():
        text = btn.inner_text().strip().replace("\n", " ")[:80]
        visible = btn.is_visible()
        enabled = btn.is_enabled()
        if text:
            print(f"  [{text}] visible={visible} enabled={enabled}")

    # Look specifically for build/spin buttons
    print("\n=== SPIN/BUILD BUTTON SEARCH ===")
    for selector in ["button:has-text('Spin')", "button:has-text('Build')", "button:has-text('spin')", "button:has-text('build')"]:
        count = page.locator(selector).count()
        print(f"  '{selector}': {count} matches")
        if count > 0:
            txt = page.locator(selector).first.inner_text().strip()
            print(f"    text: '{txt}'")
            print(f"    visible: {page.locator(selector).first.is_visible()}")

    # Scroll to bottom and screenshot
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(1000)
    page.screenshot(path="/tmp/fp_recon6_bottom.png")

    browser.close()
