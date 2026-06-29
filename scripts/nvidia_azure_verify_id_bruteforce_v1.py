#!/usr/bin/env python3
"""Try alternate ID types and capture validation."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nvidia_azure_cdp_session_guard_v1 import find_giryun288_portal

CANDIDATES = {
    "사업자 등록 ID 번호": ["6288601742", "628-86-01742", "628860174200000000000"],
    "납세자 식별 번호": ["6288601742", "628-86-01742", "1349110102309", "134911-0102309"],
}


def _frame(page):
    for fr in [page, *page.frames]:
        try:
            txt = fr.inner_text("body", timeout=2000) or ""
        except Exception:
            continue
        if "ID 유형" in txt:
            return fr
    return None


def main() -> int:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = find_giryun288_portal(browser)
        assert page
        page.bring_to_front()
        fr = _frame(page)
        if not fr:
            print("no wizard")
            return 2
        sel = fr.locator("select:visible").nth(1)
        inp = fr.locator("input[type='text']:visible").nth(7)
        for id_type, values in CANDIDATES.items():
            sel.select_option(label=id_type, timeout=5000)
            page.wait_for_timeout(800)
            for val in values:
                inp.fill(val, timeout=3000)
                page.wait_for_timeout(500)
                fr.get_by_role("button", name="다음", exact=True).click(timeout=5000)
                page.wait_for_timeout(2000)
                alerts = []
                for a in fr.locator("[role='alert']").all():
                    try:
                        t = (a.inner_text(timeout=500) or "").strip()
                        if t:
                            alerts.append(t)
                    except Exception:
                        pass
                body = fr.inner_text("body", timeout=2000) or ""
                step = "2/2" if "2/2" in body else ("1/2" if "1/2" in body else "?")
                print(f"{id_type} | {val!r} | step={step} | alerts={alerts}")
                if step == "2/2":
                    return 0
                # back if advanced? unlikely on 1/2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
