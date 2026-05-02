from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    try:
        page.goto("file:///does/not/exist.html")
        print("Success")
    except Exception as e:
        print(f"Failed: {e}")
    browser.close()
