#!/usr/bin/env python3
"""Microsoft for Startups wizard steps on portal.azure.com (post-login)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "benefits", ROOT / "scripts" / "nvidia_inception_benefits_catalog_request_v1.py"
)
benefits = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(benefits)

OUT = ROOT / "reports/nvidia_azure_wizard_latest.json"
AZURE_VIEW = (
    "https://portal.azure.com/#view/Microsoft_Azure_Startups/"
    "AzureForStartups.ReactView/skipWizardRedirect~/true"
)


def _active_frame(page):
    best = page.main_frame
    best_len = 0
    for fr in page.frames:
        try:
            txt = fr.inner_text("body", timeout=1500) or ""
        except Exception:
            continue
        if len(txt) > best_len and ("스타트업" in txt or "Startup" in txt or "다음" in txt):
            best = fr
            best_len = len(txt)
    return best


def _click_text(fr, *labels: str) -> str | None:
    for label in labels:
        for getter in (
            lambda l: fr.get_by_role("button", name=l, exact=False).first,
            lambda l: fr.get_by_role("link", name=l, exact=False).first,
            lambda l: fr.get_by_text(l, exact=False).first,
        ):
            try:
                el = getter(label)
                if el.count() and el.is_visible(timeout=2000) and el.is_enabled():
                    el.click(timeout=8000)
                    return label
            except Exception:
                continue
    return None


def _fill_wizard_step(fr, cfg: dict, pointer: dict, fills: list[str]) -> None:
    inc = pointer.get("inception", {}).get("company_form", {})
    company = str(cfg.get("company_name") or inc.get("display_name") or "mkmlab")
    website = str(cfg.get("website") or inc.get("website") or "https://jema-ai.com")
    domain = website.replace("https://", "").replace("http://", "").strip("/")
    email = str(cfg.get("contact_email") or benefits._pointer_email())
    first = str(cfg.get("first_name") or "Giryun")
    last = str(cfg.get("last_name") or "Lee")

    mapping = [
        ("Company name", company),
        ("Startup name", company),
        ("Legal name", company),
        ("Website", domain),
        ("Company website", domain),
        ("First name", first),
        ("Last name", last),
        ("Work email", email),
        ("Email", email),
        ("회사 이름", company),
        ("웹사이트", domain),
        ("이름", first),
        ("성", last),
    ]
    for label, value in mapping:
        if benefits._fill_labeled_input(fr, label, value):
            fills.append(label)
            continue
        try:
            loc = fr.get_by_label(label, exact=False).first
            if loc.count() and loc.is_visible(timeout=1000):
                loc.fill(value, timeout=5000)
                fills.append(label)
        except Exception:
            pass

    for txt in (
        "South Korea",
        "Korea, Republic of",
        "대한민국",
        "Pre-seed",
        "Seed",
        "Bootstrapped",
        "No funding",
        "Artificial intelligence",
        "AI",
        "Software",
        "B2B",
    ):
        try:
            opt = fr.get_by_text(txt, exact=False).first
            if opt.count() and opt.is_visible(timeout=800):
                opt.click(timeout=5000)
                fills.append(f"pick:{txt[:12]}")
        except Exception:
            continue

    for cb in fr.locator("input[type='checkbox']").all():
        try:
            if cb.is_visible(timeout=400) and not cb.is_checked():
                cb.check(timeout=3000)
                fills.append("checkbox")
        except Exception:
            continue


def main() -> int:
    from playwright.sync_api import sync_playwright

    answers = benefits._load_form_answers()
    cfg = answers.get("azure") or {}
    pointer = benefits._load_pointer()
    run: dict = {"steps": [], "submit_ok": False}

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = next(
            (pg for pg in browser.contexts[0].pages if "portal.azure.com" in (pg.url or "")),
            None,
        )
        if page is None:
            page = browser.contexts[0].new_page()
            page.goto(AZURE_VIEW, wait_until="domcontentloaded", timeout=120_000)
        page.bring_to_front()

        for step in range(12):
            page.wait_for_timeout(2500)
            fr = _active_frame(page)
            snippet = (fr.inner_text("body", timeout=5000) or "")[:400]
            run["steps"].append({"n": step, "snippet": snippet.replace("\n", " | ")})
            fills: list[str] = []
            _fill_wizard_step(fr, cfg, pointer, fills)

            clicked = _click_text(
                fr,
                "코드 없이 계속",
                "Continue without code",
                "다음",
                "Next",
                "Continue",
                "Submit",
                "제출",
                "신청",
                "Get started",
            )
            if clicked:
                run["steps"][-1]["clicked"] = clicked
                run["steps"][-1]["fills"] = fills
                page.wait_for_timeout(3000)
                if clicked in ("Submit", "제출", "신청"):
                    run["submit_ok"] = True
                    break
                continue

            if "LinkedIn" in snippet:
                run["human_gate"] = "linkedin_verification"
                run["hint"] = "LinkedIn으로 확인 버튼은 지휘관이 직접 클릭 (Tier-3)"
                break

            if not fills and not clicked:
                break

        run["final_snippet"] = (_active_frame(page).inner_text("body", timeout=5000) or "")[:800]
        shot = ROOT / "reports/nvidia_azure_wizard_latest.png"
        try:
            page.screenshot(path=str(shot), full_page=True, timeout=25_000)
            run["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
        except Exception:
            pass

    OUT.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0 if run.get("submit_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
