#!/usr/bin/env python3
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nvidia_azure_cdp_session_guard_v1 import find_giryun288_portal

def main() -> int:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = find_giryun288_portal(browser)
        print("page", bool(page))
        if not page:
            return 2
        page.bring_to_front()
        for i, c in enumerate([page, *page.frames]):
            try:
                t = c.inner_text("body", timeout=2000) or ""
            except Exception as e:
                print(i, "err", e)
                continue
            btns = c.get_by_role("button", name="제출", exact=True).count()
            print(i, "len", len(t), "submit_txt", "제출" in t, "btn", btns)
            if "제출" in t or btns or i == 3:
                print(t[:1200].replace("\n", "|"))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
