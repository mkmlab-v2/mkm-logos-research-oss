#!/usr/bin/env python3
from __future__ import annotations
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
        page.bring_to_front()
        for fr in [page, *page.frames]:
            try:
                txt = fr.inner_text("body", timeout=2000) or ""
            except Exception:
                continue
            if "범주" not in txt:
                continue
            cat = fr.locator("input[placeholder*='범주']").first
            cat.click(force=True, timeout=5000)
            cat.fill("Machine Learning", timeout=5000)
            page.wait_for_timeout(2000)
            for i in range(fr.locator("button").count()):
                b = fr.locator("button").nth(i)
                try:
                    if b.is_visible(timeout=200):
                        t = (b.inner_text() or "").strip()
                        if t and t not in ("다음", "취소", "시작 확인", "Horizontal Cross Industry"):
                            print("btn", i, repr(t[:100]))
                except Exception:
                    pass
            # click first suggestion-like button
            for name in ("Machine Learning", "Artificial Intelligence", "Analytics"):
                b = fr.get_by_role("button", name=name, exact=False).first
                if b.count() and b.is_visible(timeout=500):
                    b.click(timeout=3000)
                    print("clicked", name)
                    break
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
