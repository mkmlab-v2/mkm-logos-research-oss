#!/usr/bin/env python3
"""GCP startup apply 폼 채우기 (로그인 후)."""
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

OUT = ROOT / "reports/nvidia_gcp_startup_fill_latest.json"


def _find_startup_page(browser):
    for ctx in browser.contexts:
        for pg in ctx.pages:
            if "cloud.google.com/startup" in (pg.url or ""):
                return pg
    return None


def _fill_by_labels(page, mapping: list[tuple[str, str]], fills: list[str]) -> None:
    for label_sub, value in mapping:
        if not value:
            continue
        if benefits._fill_labeled_input(page, label_sub, value):
            fills.append(label_sub)
            continue
        try:
            loc = page.get_by_label(label_sub, exact=False).first
            if loc.count() and loc.is_visible(timeout=1500):
                loc.fill(value, timeout=5000)
                fills.append(label_sub)
        except Exception:
            pass


def main() -> int:
    from playwright.sync_api import sync_playwright

    cfg = benefits._load_form_answers().get("gcp") or {}
    pointer = benefits._load_pointer()
    inc = pointer.get("inception", {}).get("company_form", {})
    company = str(cfg.get("startup_company_name") or inc.get("display_name") or "mkmlab")
    website = str(cfg.get("website") or inc.get("website") or "https://jema-ai.com")
    domain = website.replace("https://", "").replace("http://", "").strip("/")
    email = str(cfg.get("google_account_email") or benefits._pointer_email())
    billing_id = str(cfg.get("billing_account_id") or "").strip()
    if not billing_id:
        try:
            import subprocess

            out = subprocess.run(
                ["gcloud", "billing", "accounts", "list", "--format=value(name)"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if out.returncode == 0 and out.stdout.strip():
                billing_id = out.stdout.strip().splitlines()[0].strip()
                run.setdefault("billing_id_source", "gcloud_cli")
        except Exception:
            pass

    run: dict = {"fills": [], "submit_ok": False}
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = _find_startup_page(browser)
        if page is None:
            page = browser.contexts[0].new_page()
            page.goto(
                "https://cloud.google.com/startup/apply?utm_content=eco_nvidia",
                wait_until="domcontentloaded",
                timeout=120_000,
            )
            page.wait_for_timeout(3000)
        page.bring_to_front()
        run["url"] = page.url[:250]

        fills: list[str] = []

        # Contact
        _fill_by_labels(
            page,
            [
                ("이름", "Giryun"),
                ("성", "Lee"),
                ("회사 이메일", email if "@no1kmedi" in email else "moksorinw@no1kmedi.com"),
            ],
            fills,
        )

        # Legal / billing section
        _fill_by_labels(
            page,
            [
                ("법적 이름", company),
                ("스타트업 법적 이름", company),
                ("웹사이트 도메인", domain),
                ("스타트업 웹사이트 도메인", domain),
                ("결제 계정", billing_id),
                ("Billing account", billing_id),
            ],
            fills,
        )

        try:
            url_inp = page.locator("input[type='url']").first
            if url_inp.count() and url_inp.is_visible(timeout=2000):
                url_inp.fill(domain, timeout=5000)
                fills.append("url_input")
        except Exception:
            pass

        if billing_id:
            try:
                vis = page.locator("input:visible").all()
                for inp in vis:
                    try:
                        t = inp.get_attribute("type") or "text"
                        if t in ("checkbox", "radio", "email", "tel", "url"):
                            continue
                        v = (inp.input_value(timeout=500) or "").strip()
                        if v in (company, domain, "ceo", "CEO"):
                            continue
                        if not v and inp.is_visible(timeout=500):
                            inp.fill(billing_id, timeout=5000)
                            fills.append("billing_id")
                            break
                    except Exception:
                        continue
            except Exception:
                pass

        # Investment: pre-funding / no institutional
        for txt in (
            "시드 이전",
            "Pre-seed",
            "pre-seed",
            "자금 조달 전",
            "아직 투자",
            "No funding",
            "Bootstrapped",
        ):
            try:
                opt = page.get_by_text(txt, exact=False).first
                if opt.count() and opt.is_visible(timeout=1000):
                    opt.click(timeout=5000)
                    fills.append(f"invest:{txt[:20]}")
                    break
            except Exception:
                continue

        for cb in page.locator("input[type='checkbox']").all():
            try:
                if cb.is_visible(timeout=500) and not cb.is_checked():
                    cb.check(timeout=3000)
                    fills.append("checkbox")
            except Exception:
                continue

        run["fills"] = fills
        run["billing_account_id_set"] = bool(billing_id)

        if not billing_id:
            run["human_gate"] = "gcp_billing_account_id_required"
            run["hint"] = (
                "GCP Console → Billing → 계정 ID 복사 후 "
                "reports/nvidia_inception_benefits_form_answers_v1.json "
                "gcp.billing_account_id 에 넣고 재실행"
            )
        else:
            errs = benefits._validation_error_count(page)
            run["validation_errors"] = errs
            if errs == 0:
                for btn in ("제출", "Submit", "신청", "Apply", "Continue", "다음"):
                    try:
                        b = page.get_by_role("button", name=btn, exact=False).first
                        if b.count() and b.is_visible(timeout=1500) and b.is_enabled():
                            b.click(timeout=8000)
                            page.wait_for_timeout(3000)
                            run["submitted"] = btn
                            run["submit_ok"] = benefits._validation_error_count(page) == 0
                            break
                    except Exception:
                        continue

        shot = ROOT / "reports/nvidia_gcp_startup_fill_latest.png"
        try:
            page.screenshot(path=str(shot), full_page=True, timeout=20_000)
            run["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
        except Exception:
            pass

    OUT.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0 if run.get("submit_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
