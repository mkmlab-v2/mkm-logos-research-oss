#!/usr/bin/env python3
"""Debug dump for Azure startups verify wizard controls."""
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
        for idx, fr in enumerate([page, *page.frames]):
            try:
                txt = fr.inner_text("body", timeout=2000) or ""
            except Exception:
                continue
            if "ID 유형" not in txt and "1/2" not in txt:
                continue
            print(f"\n=== target {idx} url={fr.url[:120]} ===")
            for sel in (
                "button",
                "[role='combobox']",
                "[role='listbox']",
                "input",
                "select",
            ):
                loc = fr.locator(sel)
                n = min(loc.count(), 20)
                for i in range(n):
                    el = loc.nth(i)
                    try:
                        if not el.is_visible(timeout=300):
                            continue
                        tag = el.evaluate("e => e.tagName")
                        role = el.get_attribute("role") or ""
                        aria = el.get_attribute("aria-label") or ""
                        txt2 = (el.inner_text(timeout=300) or "")[:80]
                        ph = el.get_attribute("placeholder") or ""
                        val = ""
                        if tag == "INPUT":
                            val = el.input_value(timeout=300)
                        print(f"  {sel}[{i}] tag={tag} role={role} aria={aria!r} ph={ph!r} val={val!r} text={txt2!r}")
                    except Exception as e:
                        print(f"  {sel}[{i}] err={e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
