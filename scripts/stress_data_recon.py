"""
Deep recon: do ONE complete build and dump the full text from every screen.
Goal: find every data point (cost, salary, stats, bosses) and where it appears.
"""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    # --- PROFILE ---
    page.goto("http://localhost:5173/profile")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)
    page.select_option("#home-state", "IN")
    page.locator("text=Let's go").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # --- SET YOUR COURSE ---
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

    # Click a mid-range career
    for card in cards:
        if "operations manager" in card.inner_text().lower():
            card.click()
            break
    else:
        cards[len(cards)//2].click()

    page.wait_for_timeout(1000)

    # DUMP: full text of Set Your Course page
    syc_text = page.inner_text("body")
    with open("/tmp/fp_dump_setyourcourse.txt", "w") as f:
        f.write(syc_text)
    page.screenshot(path="/tmp/fp_dump_setyourcourse.png", full_page=True)
    print("=== SET YOUR COURSE — key data lines ===")
    for line in syc_text.split("\n"):
        line = line.strip()
        if any(kw in line.lower() for kw in ["$", "cost", "price", "tuition", "debt", "loan", "salary", "wage", "earn", "ern", "roi", "res", "grw", "aura", "financing", "4 years", "4yr", "published"]):
            print(f"  {line[:120]}")

    # --- BUILD ---
    build_btn = None
    for b in page.locator("button").all():
        if "spec my build" in b.inner_text().lower():
            build_btn = b
            break
    build_btn.scroll_into_view_if_needed()
    build_btn.click()

    page.wait_for_timeout(15000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    # DUMP: full text of Build Results page
    results_text = page.inner_text("body")
    with open("/tmp/fp_dump_mybuild.txt", "w") as f:
        f.write(results_text)
    page.screenshot(path="/tmp/fp_dump_mybuild.png", full_page=True)
    print("\n=== MY BUILD — key data lines ===")
    for line in results_text.split("\n"):
        line = line.strip()
        if any(kw in line.lower() for kw in ["$", "cost", "price", "tuition", "debt", "loan", "salary", "wage", "earn", "ern", "roi", "res", "grw", "aura", "win", "loss", "draw", "median", "/10", "score"]):
            print(f"  {line[:120]}")

    # Click "Save This Build" at bottom
    save_btn = page.locator("button", has_text="Save This Build")
    if save_btn.count() > 0:
        save_btn.scroll_into_view_if_needed()
        save_btn.click()
        page.wait_for_timeout(3000)
        print(f"\nAfter Save URL: {page.url}")

    # --- BUILDS MENU ---
    page.goto("http://localhost:5173/builds")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    menu_text = page.inner_text("body")
    with open("/tmp/fp_dump_builds.txt", "w") as f:
        f.write(menu_text)
    page.screenshot(path="/tmp/fp_dump_builds.png", full_page=True)
    print("\n=== BUILDS MENU — key data lines ===")
    for line in menu_text.split("\n"):
        line = line.strip()
        if any(kw in line.lower() for kw in ["$", "cost", "price", "ern", "roi", "res", "grw", "aura", "win", "loss", "draw", "w", "l", "salary", "earn", "/10"]):
            print(f"  {line[:120]}")

    browser.close()
    print("\nText dumps written to /tmp/fp_dump_*.txt")
    print("Screenshots written to /tmp/fp_dump_*.png")
