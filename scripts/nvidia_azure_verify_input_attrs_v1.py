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
        assert page
        for fr in [page, *page.frames]:
            try:
                txt = fr.inner_text("body", timeout=2000) or ""
            except Exception:
                continue
            if "사업자 등록" not in txt:
                continue
            inp = fr.locator("input[type='text']:visible").nth(7)
            print("maxlength", inp.get_attribute("maxlength"))
            print("minlength", inp.get_attribute("minlength"))
            print("pattern", inp.get_attribute("pattern"))
            print("val", inp.input_value())
            sel = fr.locator("select:visible").nth(1)
            for j in range(sel.locator("option").count()):
                print("opt", j, sel.locator("option").nth(j).inner_text())
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
