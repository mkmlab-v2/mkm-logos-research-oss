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
        page.bring_to_front()
        for c in [page, *page.frames]:
            try:
                t = c.inner_text("body", timeout=3000) or ""
            except Exception:
                continue
            if len(t) > 200:
                for kw in ("제출", "검토", "pending", "확인 중", "시작 확인", "인증", "verified", "submitted"):
                    if kw in t:
                        print("frame hit", kw)
                if "제출" in t or "검토" in t or "시작 확인" in t:
                    print(t[:1500])
        page.screenshot(path=str(ROOT/"reports/nvidia_azure_status_latest.png"), full_page=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
