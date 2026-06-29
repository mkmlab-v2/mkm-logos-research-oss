#!/usr/bin/env python3
"""Reopen verify wizard if needed, reach review, consent, 제출."""
from __future__ import annotations
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nvidia_azure_cdp_session_guard_v1 import find_giryun288_portal

OUT = ROOT / "reports/nvidia_azure_verify_final_submit_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _find_review_frame(page):
    for candidate in [page, *page.frames]:
        try:
            txt = candidate.inner_text("body", timeout=2000) or ""
        except Exception:
            continue
        if "제출" in txt and ("개인정보" in txt or "주소" in txt or "스타트업" in txt):
            return candidate
        try:
            if candidate.get_by_role("button", name="제출", exact=True).count():
                return candidate
        except Exception:
            continue
    return None


def _open_wizard(page, run: dict) -> None:
    for target in [page, *page.frames]:
        for sel in ("button:has-text('시작 확인')", "a:has-text('시작 확인')"):
            try:
                loc = target.locator(sel).first
                if loc.count() and loc.is_visible(timeout=1500):
                    loc.click(timeout=8000)
                    page.wait_for_timeout(5000)
                    run["reopened"] = sel
                    return
            except Exception:
                continue
        for label in ("확인 시작", "Start verification"):
            try:
                loc = target.get_by_role("button", name=label, exact=False).first
                if loc.count() and loc.is_visible(timeout=1500):
                    loc.click(timeout=8000)
                    page.wait_for_timeout(5000)
                    run["reopened"] = label
                    return
            except Exception:
                continue


def main() -> int:
    from playwright.sync_api import sync_playwright

    run = {"schema": "nvidia_azure_verify_final_submit_v1", "generated_at_utc": _utc()}
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = find_giryun288_portal(browser)
        if not page:
            run["error"] = "no_portal"
            OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 2
        page.bring_to_front()

        fr = _find_review_frame(page)
        if not fr:
            _open_wizard(page, run)
            page.wait_for_timeout(3000)
            fr = _find_review_frame(page)
            if not fr:
                for c in [page, *page.frames]:
                    try:
                        t = c.inner_text("body", timeout=2000) or ""
                        if t:
                            run["after_reopen_snippet"] = t[:500].replace("\n", " | ")
                            if "1/2" in t or "2/2" in t or "확인 시작" in t:
                                run["wizard_state"] = (
                                    "1/2" if "1/2" in t else ("2/2" if "2/2" in t else "intro")
                                )
                                break
                    except Exception:
                        continue

        if not fr:
            # maybe on 2/2 — run step2 submit helper
            body = ""
            for c in [page, *page.frames]:
                try:
                    body = c.inner_text("body", timeout=2000) or ""
                    if "2/2" in body or "LinkedIn" in body:
                        run["delegate"] = "step2_submit"
                        break
                except Exception:
                    continue
            if run.get("delegate"):
                OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                rc = subprocess.call([sys.executable, str(ROOT / "scripts" / "nvidia_azure_verify_step2_submit_v1.py")])
                with sync_playwright() as p2:
                    browser2 = p2.chromium.connect_over_cdp("http://127.0.0.1:9222")
                    page2 = find_giryun288_portal(browser2)
                    if page2:
                        page2.bring_to_front()
                        fr = _find_review_frame(page2)
                        page = page2
                if not fr:
                    run["error"] = "no_review_after_step2"
                    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    return 2
            else:
                run["error"] = "no_review_panel"
                OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                return 2

        checked = 0
        for i in range(fr.locator("input[type='checkbox']").count()):
            cb = fr.locator("input[type='checkbox']").nth(i)
            try:
                if not cb.is_checked():
                    cb.check(force=True, timeout=3000)
                checked += 1
            except Exception:
                try:
                    fr.locator("input[type='checkbox']").nth(i).click(force=True, timeout=3000)
                    checked += 1
                except Exception:
                    pass
        run["consent_checked"] = checked

        btn = fr.get_by_role("button", name="제출", exact=True).first
        if not btn.count():
            btn = fr.locator("button:has-text('제출')").first
        btn.click(timeout=8000)
        page.wait_for_timeout(12000)

        body = ""
        for candidate in [page, *page.frames]:
            try:
                t = candidate.inner_text("body", timeout=3000) or ""
                if len(t) > len(body):
                    body = t
            except Exception:
                continue
        run["body_snippet"] = body[:1000].replace("\n", " | ")
        run["submitted"] = any(
            k in body
            for k in (
                "검토",
                "제출되",
                "감사",
                "Thank",
                "review",
                "pending",
                "확인 중",
                "submitted",
                "접수",
            )
        )
        page.screenshot(path=str(ROOT / "reports/nvidia_azure_verify_final_submit_latest.png"), full_page=True)

    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0 if run.get("submitted") else 1


if __name__ == "__main__":
    raise SystemExit(main())
