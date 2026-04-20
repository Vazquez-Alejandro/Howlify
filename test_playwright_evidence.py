from playwright.sync_api import sync_playwright
import os

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox','--disable-dev-shm-usage'])
    page = browser.new_page()
    page.goto("https://example.com", timeout=60000, wait_until="networkidle")
    os.makedirs("evidence", exist_ok=True)
    path = "evidence/test_example.png"
    page.screenshot(path=path, full_page=True)
    browser.close()
    print("✅ Saved:", path, "size:", os.path.getsize(path))
