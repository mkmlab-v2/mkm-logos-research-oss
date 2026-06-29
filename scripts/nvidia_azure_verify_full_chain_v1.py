#!/usr/bin/env python3
"""Fix KR state/zip, advance 1/2 -> 2/2 -> review -> submit."""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nvidia_azure_cdp_session_guard_v1 import find_giryun288_portal

OUT = ROOT / "reports/nvidia_azure_verify_full_chain_latest.json"
ENTITY = "주식회사 목소리네트워크"
BRN = "628860174200000000000"
LINKEDIN = "https://www.linkedin.com/in/mkm-ai-2b7769391"
DESC = (
    "MKM Lab — AI-assisted risk warning and exposure control. B2B document compression, "
    "RAG, reproducible ops metrics. https://jema-ai.com"
)
WEBSITE = "https://jema-ai.com"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _frame_with(page, *needles: str):
    for c in [page, *page.frames]:
        try:
            t = c.inner_text("body", timeout=2000) or ""
        except Exception:
            continue
        if all(n in t for n in needles):
            return c
        if needles[0] in t and len(needles) == 1:
            return c
    return None


def _fill_step1(page, fr, run: dict) -> bool:
    ins = fr.locator("input[type='text']:visible")
    fr.locator("select:visible").nth(0).select_option(label="대한민국")
    page.wait_for_timeout(500)
    ins.nth(0).fill(ENTITY, timeout=5000)
    ins.nth(4).fill("Gwangmyeong", timeout=5000)
    ins.nth(5).fill("", timeout=2000)
    ins.nth(5).type("경기", delay=50)
    ins.nth(5).press("Tab")
    page.wait_for_timeout(800)
    ins.nth(6).fill("", timeout=2000)
    ins.nth(6).type("14267", delay=50)
    ins.nth(6).press("Tab")
    page.wait_for_timeout(800)
    fr.locator("select:visible").nth(1).select_option(label="사업자 등록 ID 번호")
    ins.nth(7).fill(BRN, timeout=5000)
    page.wait_for_timeout(1200)
    err = ins.nth(5).evaluate(
        """el => (el.closest('.fui-Field')||el.parentElement)?.querySelector('[role=alert]')?.innerText || ''"""
    )
    err2 = ins.nth(6).evaluate(
        """el => (el.closest('.fui-Field')||el.parentElement)?.querySelector('[role=alert]')?.innerText || ''"""
    )
    run["step1_errors"] = [err, err2]
    if err or err2:
        return False
    fr.get_by_role("button", name="다음", exact=True).click(timeout=8000)
    page.wait_for_timeout(8000)
    return True


def _fill_step2(page, fr, run: dict) -> None:
    fr.locator("textarea:visible").first.fill(DESC, timeout=5000)
    fr.locator("input[placeholder*='웹']").first.fill(WEBSITE, timeout=5000)
    fr.locator("input[placeholder*='LinkedIn']").first.fill(LINKEDIN, timeout=5000)
    cat = fr.locator("input[placeholder*='범주']").first
    picked = []
    for term in ("Machine Learning", "Artificial Intelligence"):
        cat.click(force=True, timeout=3000)
        cat.fill(term, timeout=5000)
        page.wait_for_timeout(1000)
        btn = fr.get_by_role("button", name=term, exact=False).first
        if btn.count() and btn.is_visible(timeout=800):
            btn.click(timeout=3000)
            picked.append(term)
    run["categories"] = picked
    if fr.get_by_role("combobox").filter(has_text="선택").count():
        fr.get_by_role("combobox").filter(has_text="선택").first.click(timeout=5000)
        page.wait_for_timeout(1000)
        opt = fr.get_by_role("option", name="Horizontal Cross Industry", exact=False).first
        if opt.count():
            opt.click(timeout=3000)
    for text in ("MVP 빌드 및 유효성 검사", "AI/ML 기능 통합", "운영 비용 절감"):
        fr.get_by_text(text, exact=True).first.click(timeout=3000)
    fr.get_by_role("button", name="다음", exact=True).click(timeout=8000)
    page.wait_for_timeout(8000)


def _submit_review(page, fr, run: dict) -> None:
    for i in range(fr.locator("input[type='checkbox']").count()):
        cb = fr.locator("input[type='checkbox']").nth(i)
        try:
            if not cb.is_checked():
                cb.check(force=True, timeout=3000)
        except Exception:
            cb.click(force=True, timeout=3000)
    fr.get_by_role("button", name="제출", exact=True).click(timeout=8000)
    page.wait_for_timeout(12000)


def main() -> int:
    from playwright.sync_api import sync_playwright

    run = {"schema": "nvidia_azure_verify_full_chain_v1", "generated_at_utc": _utc()}
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = find_giryun288_portal(browser)
        if not page:
            run["error"] = "no_portal"
            OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 2
        page.bring_to_front()

        fr = _frame_with(page, "제출") or _frame_with(page, "2/2") or _frame_with(page, "1/2")
        if not fr:
            for target in [page, *page.frames]:
                for sel in ("button:has-text('시작 확인')",):
                    try:
                        loc = target.locator(sel).first
                        if loc.count() and loc.is_visible(timeout=1500):
                            loc.click(timeout=8000)
                            page.wait_for_timeout(3000)
                    except Exception:
                        pass
                try:
                    loc = target.get_by_role("button", name="확인 시작", exact=False).first
                    if loc.count() and loc.is_visible(timeout=1500):
                        loc.click(timeout=8000)
                        page.wait_for_timeout(3000)
                except Exception:
                    pass
            fr = _frame_with(page, "1/2")

        if fr and "1/2" in (fr.inner_text("body", timeout=2000) or ""):
            run["phase"] = "step1"
            if not _fill_step1(page, fr, run):
                page.screenshot(path=str(ROOT / "reports/nvidia_azure_verify_full_chain_latest.png"), full_page=True)
                OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print(json.dumps(run, ensure_ascii=False, indent=2))
                return 1
            run["step1_ok"] = True

        fr = _frame_with(page, "제출") or _frame_with(page, "2/2") or _frame_with(page, "LinkedIn")
        if not fr:
            for c in [page, *page.frames]:
                try:
                    t = c.inner_text("body", timeout=2000) or ""
                except Exception:
                    continue
                if "LinkedIn" in t or "2/2" in t:
                    fr = c
                    break

        if fr and ("2/2" in (fr.inner_text("body", timeout=2000) or "") or "LinkedIn" in (fr.inner_text("body", timeout=2000) or "")):
            run["phase"] = "step2"
            _fill_step2(page, fr, run)
            run["step2_ok"] = True
            fr = _frame_with(page, "제출")
            if not fr:
                for c in [page, *page.frames]:
                    try:
                        t = c.inner_text("body", timeout=2000) or ""
                    except Exception:
                        continue
                    if "제출" in t and "개인정보" in t:
                        fr = c
                        break

        if fr and "제출" in (fr.inner_text("body", timeout=2000) or ""):
            run["phase"] = "review"
            _submit_review(page, fr, run)
            run["submitted"] = True

        page.screenshot(path=str(ROOT / "reports/nvidia_azure_verify_full_chain_latest.png"), full_page=True)

    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0 if run.get("submitted") else 1


if __name__ == "__main__":
    raise SystemExit(main())
