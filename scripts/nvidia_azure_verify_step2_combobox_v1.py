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
            if "2/2" not in txt:
                continue
            for sel in ("button", "[role='combobox']", "[role='listbox']", "label"):
                n = min(fr.locator(sel).count(), 25)
                for i in range(n):
                    el = fr.locator(sel).nth(i)
                    try:
                        if not el.is_visible(timeout=200):
                            continue
                        t = (el.inner_text(timeout=300) or "")[:100]
                        aria = el.get_attribute("aria-label") or ""
                        if t or aria:
                            print(f"{sel}[{i}] aria={aria!r} text={t!r}")
                    except Exception:
                        pass
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
