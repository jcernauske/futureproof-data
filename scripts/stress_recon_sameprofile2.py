"""Test: use in-page navigation (not page.goto) to keep Zustand profile state."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    # Create profile
    page.goto("http://localhost:5173/profile")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)
    profile_name = page.locator("h1, h2").first.inner_text().strip()
    print(f"Profile: {profile_name}")
    page.select_option("#home-state", "IN")
    page.locator("text=Let's go").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # Build 1
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

    # Try "Start over" button (should be on results page)
    start_over = page.locator("button, a", has_text="Start over")
    print(f"'Start over' buttons: {start_over.count()}")

    # Try using React Router navigation via JS
    print("\nTrying JS-based navigation...")
    page.evaluate("window.history.pushState({}, '', '/set-your-course')")
    page.wait_for_timeout(500)
    # That won't trigger React Router. Try dispatching a popstate event:
    page.evaluate("""
        window.history.pushState({}, '', '/set-your-course');
        window.dispatchEvent(new PopStateEvent('popstate'));
    """)
    page.wait_for_timeout(2000)
    print(f"After JS nav: {page.url}")
    search2 = page.locator("input[placeholder*='Search for your school']")
    print(f"School search: {search2.count()}")

    if search2.count() == 0:
        # Try clicking "Start over" link
        if start_over.count() > 0:
            start_over.first.click()
            page.wait_for_timeout(2000)
            print(f"After 'Start over': {page.url}")
            search3 = page.locator("input[placeholder*='Search for your school']")
            print(f"School search: {search3.count()}")

    # Last resort: check all nav links/buttons
    print("\nAll clickable nav elements:")
    for el in page.locator("a, button").all():
        text = el.inner_text().strip()[:50]
        href = el.get_attribute("href") or ""
        if text and ("build" in text.lower() or "start" in text.lower() or "course" in text.lower() or "set" in text.lower()):
            print(f"  [{text}] href={href}")

    browser.close()
