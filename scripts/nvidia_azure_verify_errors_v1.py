#!/usr/bin/env python3
"""Capture validation messages in Azure verify wizard."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nvidia_azure_cdp_session_guard_v1 import find_giryun288_portal


def main() -> int:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = find_giryun288_portal(browser)
        if page is None:
            print("no portal tab")
            return 2
        page.bring_to_front()
        for fr in [page, *page.frames]:
            try:
                txt = fr.inner_text("body", timeout=2000) or ""
            except Exception:
                continue
            if "사업자 등록" not in txt and "1/2" not in txt:
                continue
            print("=== body excerpt ===")
            for line in txt.splitlines():
                line = line.strip()
                if not line:
                    continue
                if any(k in line for k in ("필수", "오류", "error", "invalid", "유효", "확인", "사업자", "ID", "1/2", "2/2")):
                    print(line)
            for sel in ("[class*='error']", "[role='alert']", ".ms-MessageBar--error", "span"):
                loc = fr.locator(sel)
                n = min(loc.count(), 40)
                for i in range(n):
                    el = loc.nth(i)
                    try:
                        if not el.is_visible(timeout=200):
                            continue
                        t = (el.inner_text(timeout=200) or "").strip()
                        if t and any(k in t for k in ("필수", "오류", "유효", "형식", "확인", "등록")):
                            print(f"ERR[{sel}][{i}]: {t}")
                    except Exception:
                        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
