#!/usr/bin/env python3
"""Nebius billing form — prefill non-payment fields only (card = Tier-3 human)."""
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

OUT = ROOT / "reports/nvidia_nebius_billing_prefill_latest.json"
PAYMENTS_URL = "https://console.nebius.com/tenant-e00fe2zhs67gmz6wha/billing/payments"


def _fill_if_empty(page, label: str, value: str, fills: list[str]) -> None:
    if not value:
        return
    try:
        loc = page.get_by_label(label, exact=False).first
        if loc.count() and loc.is_visible(timeout=2000):
            cur = (loc.input_value(timeout=1000) or "").strip()
            if not cur:
                loc.fill(value, timeout=5000)
                fills.append(label)
                return
    except Exception:
        pass
    if benefits._fill_labeled_input(page, label, value):
        fills.append(f"lbl:{label}")
        return
    # Nebius billing: label text is sibling of input (not always wired to <label for>)
    try:
        safe = label.replace("(", r"\(").replace(")", r"\)")
        lbl = page.locator(f"text=/{safe}/i").first
        if lbl.count() and lbl.is_visible(timeout=1500):
            inp = lbl.locator("xpath=following::input[not(@type='hidden')][1]")
            if inp.count() and inp.is_visible(timeout=1500):
                cur = (inp.input_value(timeout=1000) or "").strip()
                if not cur:
                    inp.fill(value, timeout=5000)
                    fills.append(f"xpath:{label}")
    except Exception:
        pass


def main() -> int:
    from playwright.sync_api import sync_playwright

    answers = benefits._load_form_answers()
    nebius = answers.get("nebius") or {}
    gcp = answers.get("gcp") or {}
    first = str(nebius.get("first_name") or gcp.get("contact_first_name") or "Giryun")
    last = str(nebius.get("last_name") or gcp.get("contact_last_name") or "Lee")
    bill_email = str(gcp.get("google_account_email") or "moksorinw@gmail.com")
    street = str(nebius.get("billing_street_en") or "880 Gwangmyeong-ro")
    city = str(nebius.get("billing_city_en") or "Gwangmyeong")
    postal = str(nebius.get("billing_postal_code") or "14267")

    run: dict = {"fills": [], "submit_ok": False, "payments_url": PAYMENTS_URL}

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = browser.contexts[0].new_page()
        page.goto(PAYMENTS_URL, wait_until="domcontentloaded", timeout=120_000)
        page.bring_to_front()
        page.wait_for_timeout(5000)

        # Individual (default) vs Company
        try:
            ind = page.get_by_text("Individual", exact=False).first
            if ind.count() and ind.is_visible(timeout=2000):
                ind.click(timeout=5000)
                run["fills"].append("individual")
        except Exception:
            pass

        fills: list[str] = []
        for label, val in (
            ("First name", first),
            ("Last name", last),
            ("Billing notification email", bill_email),
            ("Street and house number", street),
            ("City", city),
            ("Postal code", postal),
        ):
            _fill_if_empty(page, label, val, fills)

        # Country dropdown
        for country in ("South Korea", "Korea, Republic of", "Korea"):
            try:
                loc = page.get_by_label("Country of residence", exact=False).first
                if loc.count() and loc.is_visible(timeout=1500):
                    loc.click(timeout=3000)
                    page.get_by_text(country, exact=False).first.click(timeout=5000)
                    fills.append(f"country:{country}")
                    break
            except Exception:
                continue
        if not any(f.startswith("country:") for f in fills):
            try:
                cr = page.get_by_text("Country of residence", exact=False).first
                if cr.count() and cr.is_visible(timeout=1500):
                    cr.click(timeout=3000)
                    page.get_by_text("South Korea", exact=False).first.click(timeout=5000)
                    fills.append("country:South Korea")
            except Exception:
                pass
        if not any("City" in f for f in fills):
            try:
                city_inp = page.locator("input").filter(
                    has=page.locator("xpath=preceding::*[contains(., 'City')][1]")
                ).first
                if city_inp.count() and city_inp.is_visible(timeout=1500):
                    if not (city_inp.input_value(timeout=500) or "").strip():
                        city_inp.fill(city, timeout=5000)
                        fills.append("City")
            except Exception:
                pass

        try:
            cb = page.get_by_text("I confirm that I agree", exact=False).first
            if cb.count():
                cb.click(timeout=5000)
                fills.append("terms_click")
        except Exception:
            pass
        for cb in page.locator("input[type='checkbox']").all():
            try:
                if cb.is_visible(timeout=500) and not cb.is_checked():
                    cb.check(timeout=3000)
                    fills.append("checkbox")
            except Exception:
                continue

        run["fills"] = fills
        body = page.inner_text("body", timeout=8000) or ""
        run["needs_street"] = "Street and house number" in body
        run["needs_card"] = "Card details" in body or "Add card" in body
        run["human_gate"] = "nebius_billing_address_and_card_tier3"
        run["hint"] = (
            "Payments 화면에서 주소(Street/City/Postal) + 카드 입력 후 "
            "'Save billing details' 클릭 ($25 입금). 카드는 지휘관만."
        )
        run["billing_email_seen"] = bill_email if bill_email in body else "check_ui"

        shot = ROOT / "reports/nvidia_nebius_billing_prefill_latest.png"
        page.screenshot(path=str(shot), full_page=True, timeout=25_000)
        run["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")

    OUT.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
