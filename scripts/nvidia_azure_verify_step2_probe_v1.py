#!/usr/bin/env python3
"""Probe step 2/2 fields."""
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
            if "2/2" not in txt and "LinkedIn" not in txt:
                continue
            print("=== inputs ===")
            for i in range(min(fr.locator("input:visible, textarea:visible").count(), 15)):
                el = fr.locator("input:visible, textarea:visible").nth(i)
                tag = el.evaluate("e => e.tagName")
                ph = el.get_attribute("placeholder") or ""
                val = el.input_value() if tag == "INPUT" else el.inner_text()[:60]
                print(i, tag, ph, repr(val))
            print("=== selects ===")
            for i in range(fr.locator("select:visible").count()):
                sel = fr.locator("select:visible").nth(i)
                opts = [sel.locator("option").nth(j).inner_text()[:60] for j in range(min(sel.locator("option").count(), 15))]
                print(i, opts)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
