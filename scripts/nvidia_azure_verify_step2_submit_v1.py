#!/usr/bin/env python3
"""Fill step 2/2 completely and submit."""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nvidia_azure_cdp_session_guard_v1 import find_giryun288_portal

OUT = ROOT / "reports/nvidia_azure_verify_step2_submit_latest.json"
DESC = (
    "MKM Lab — AI-assisted risk warning and exposure control. B2B document compression, "
    "RAG, and reproducible ops metrics. https://jema-ai.com"
)
WEBSITE = "https://jema-ai.com"
LINKEDIN = "https://www.linkedin.com/in/mkm-ai-2b7769391"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _wizard_frame(page):
    for fr in [page, *page.frames]:
        try:
            txt = fr.inner_text("body", timeout=2000) or ""
        except Exception:
            continue
        if "2/2" in txt or "LinkedIn" in txt:
            return fr
    return None


def main() -> int:
    from playwright.sync_api import sync_playwright

    run = {"schema": "nvidia_azure_verify_step2_submit_v1", "generated_at_utc": _utc()}
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = find_giryun288_portal(browser)
        if not page:
            run["error"] = "no_portal"
            OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 2
        page.bring_to_front()
        fr = _wizard_frame(page)
        if not fr:
            run["error"] = "no_wizard"
            OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 2

        fr.locator("textarea:visible").first.fill(DESC, timeout=5000)
        fr.locator("input[placeholder*='웹']").first.fill(WEBSITE, timeout=5000)
        fr.locator("input[placeholder*='LinkedIn']").first.fill(LINKEDIN, timeout=5000)
        run["core_fields"] = True

        # categories — type Korean label + Enter (listbox commit)
        picked = []
        cat = fr.locator("input[placeholder*='범주']").first
        for label in ("인공 지능",):
            cat.click(force=True, timeout=3000)
            cat.fill(label, timeout=5000)
            page.wait_for_timeout(800)
            cat.press("Enter")
            page.wait_for_timeout(600)
            picked.append(label)
        fr.locator("textarea:visible").first.click(timeout=3000)
        page.wait_for_timeout(400)
        run["categories"] = picked

        # goals — after category (category click can reset checkboxes)
        goals = []
        for text in (
            "MVP 빌드 및 유효성 검사",
            "AI/ML 기능 통합",
            "운영 비용 절감",
        ):
            try:
                t = fr.get_by_text(text, exact=True).first
                if t.count() and t.is_visible(timeout=1000):
                    t.click(timeout=3000)
                    page.wait_for_timeout(300)
                    goals.append(text)
            except Exception:
                pass
        run["goals"] = goals

        checked = []
        for i in range(fr.locator("input[type='checkbox']").count()):
            cb = fr.locator("input[type='checkbox']").nth(i)
            try:
                if cb.is_checked():
                    checked.append(i)
            except Exception:
                pass
        run["checked_indices"] = checked

        fr.get_by_role("button", name="다음", exact=True).click(timeout=8000)
        page.wait_for_timeout(8000)

        body = fr.inner_text("body", timeout=3000) or ""
        run["step_after"] = "closed" if "2/2" not in body else "2/2"
        if "[role='alert']" in body or "필수" in body:
            alerts = []
            for a in fr.locator("[role='alert']").all():
                try:
                    t = (a.inner_text(timeout=500) or "").strip()
                    if t:
                        alerts.append(t)
                except Exception:
                    pass
            run["alerts"] = alerts

        page.screenshot(path=str(ROOT / "reports/nvidia_azure_verify_step2_submit_latest.png"), full_page=True)

    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0 if run.get("step_after") == "closed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
