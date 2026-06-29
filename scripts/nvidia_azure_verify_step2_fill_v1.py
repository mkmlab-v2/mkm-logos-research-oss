#!/usr/bin/env python3
"""Fill step 2/2 except LinkedIn."""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nvidia_azure_cdp_session_guard_v1 import find_giryun288_portal

OUT = ROOT / "reports/nvidia_azure_verify_step2_fill_latest.json"
DESC = (
    "MKM Document Intelligence Platform — B2B document compression and RAG for enterprises. "
    "Research harness on local GPU; evaluating TensorRT-LLM/vLLM on Azure. https://jema-ai.com"
)
WEBSITE = "https://jema-ai.com"
LINKEDIN = "https://www.linkedin.com/in/mkm-ai-2b7769391"
CAT_KEYWORDS = ("AI", "Machine Learning", "인공지능", "Software", "Analytics", "Data")
IND_KEYWORDS = ("Information", "Software", "Technology", "정보", "소프트웨어")
GOAL_LABELS = ("MVP 빌드", "AI/ML", "운영 비용")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _wizard_frame(page):
    for fr in [page, *page.frames]:
        try:
            txt = fr.inner_text("body", timeout=2000) or ""
        except Exception:
            continue
        if "2/2" in txt:
            return fr
    return None


def main() -> int:
    from playwright.sync_api import sync_playwright

    run = {"schema": "nvidia_azure_verify_step2_fill_v1", "generated_at_utc": _utc()}
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
            run["error"] = "no_step2"
            OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 2

        ta = fr.locator("textarea:visible").first
        ta.fill(DESC, timeout=5000)
        run["description"] = True

        inputs = fr.locator("input[type='text']:visible")
        if inputs.count() >= 1:
            inputs.nth(0).fill(WEBSITE, timeout=5000)
            run["website"] = WEBSITE

        li = fr.locator("input[placeholder*='LinkedIn']").first
        if li.count():
            li.fill(LINKEDIN, timeout=5000)
            run["linkedin_value"] = LINKEDIN

        # category multiselect (Fluent tag picker — type + click suggestion button)
        try:
            cat = fr.locator("input[placeholder*='범주']").first
            cat.click(force=True, timeout=5000)
            picked = []
            for term in ("Machine Learning", "Artificial Intelligence", "Analytics"):
                cat.fill(term, timeout=5000)
                page.wait_for_timeout(1200)
                btn = fr.get_by_role("button", name=term, exact=False).first
                if btn.count() and btn.is_visible(timeout=800):
                    btn.click(timeout=3000)
                    picked.append(term)
                    page.wait_for_timeout(500)
                if len(picked) >= 2:
                    break
            run["categories"] = picked
        except Exception as exc:
            run["category_error"] = str(exc)[:200]

        # industry combobox
        try:
            ind = fr.get_by_role("combobox").filter(has_text="선택").first
            ind.click(timeout=5000)
            page.wait_for_timeout(1200)
            for opt_name in (
                "Horizontal Cross Industry",
                "Software",
                "Information Technology",
                "Financial Services",
            ):
                opt = fr.get_by_role("option", name=opt_name, exact=False).first
                if not opt.count():
                    opt = page.get_by_text(opt_name, exact=False).first
                if opt.count() and opt.is_visible(timeout=800):
                    opt.click(timeout=3000)
                    run["industry"] = opt_name
                    break
        except Exception as exc:
            run["industry_error"] = str(exc)[:200]

        # Azure goals checkboxes
        goals = []
        for label in (
            "MVP 빌드 및 유효성 검사",
            "AI/ML 기능 통합",
            "운영 비용 절감",
        ):
            try:
                row = fr.locator(f"label:has-text('{label}')").first
                if row.count():
                    row.click(timeout=3000)
                    goals.append(label)
            except Exception:
                pass
        run["goals"] = goals

        page.wait_for_timeout(1000)
        try:
            nxt = fr.get_by_role("button", name="다음", exact=True).first
            if nxt.count() and nxt.is_visible(timeout=2000):
                nxt.click(timeout=8000)
                page.wait_for_timeout(6000)
                run["clicked_next"] = True
        except Exception as exc:
            run["next_error"] = str(exc)[:200]

        body = ""
        for target in [page, *page.frames]:
            try:
                body = target.inner_text("body", timeout=2000) or ""
                if "2/2" in body or "제출" in body or "확인" in body:
                    break
            except Exception:
                continue
        run["step_after"] = (
            "submitted" if "검토" in body or "제출" in body and "2/2" not in body
            else ("2/2" if "2/2" in body else "unknown")
        )
        if any(k in body for k in ("오류", "필수", "유효하지")):
            run["validation_hint"] = body[:400].replace("\n", " | ")

        page.screenshot(path=str(ROOT / "reports/nvidia_azure_verify_step2_fill_latest.png"), full_page=True)

    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
