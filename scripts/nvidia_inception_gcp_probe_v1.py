#!/usr/bin/env python3
"""Probe + GCP benefit request when CDP session available."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "autofill", ROOT / "scripts" / "nvidia_inception_portal_product_autofill_v1.py"
)
autofill = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(autofill)

_spec2 = importlib.util.spec_from_file_location(
    "benefits", ROOT / "scripts" / "nvidia_inception_benefits_catalog_request_v1.py"
)
benefits = importlib.util.module_from_spec(_spec2)
assert _spec2.loader is not None
_spec2.loader.exec_module(benefits)

GCP_TITLE = "$2,000-$350,000 in Google Cloud Credits"
OUT = ROOT / "reports/nvidia_gcp_benefit_request_latest.json"


def main() -> int:
    from playwright.sync_api import sync_playwright

    run: dict = {"steps": []}
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        autofill._inject_storage_state(context)
        page = context.pages[0] if context.pages else context.new_page()

        page.goto(
            "https://programs.nvidia.com/phoenix/benefits",
            wait_until="domcontentloaded",
            timeout=120_000,
        )
        page.wait_for_timeout(2500)
        run["steps"].append({"phoenix": page.url[:200]})

        autofill._try_phoenix_email_gate(page)
        benefits._try_nvidia_sso_email(page)

        deadline = time.time() + 180
        while time.time() < deadline:
            if benefits._catalog_logged_in(page) or autofill._logged_in(page):
                if "login.nvgs" not in page.url:
                    break
            page.wait_for_timeout(3000)

        bootstrap, page = benefits._bootstrap_session(page, context)
        run["bootstrap"] = bootstrap
        run["url_after_bootstrap"] = page.url[:200]

        if not benefits._catalog_logged_in(page):
            run["error"] = "login_required — complete NVIDIA login in Chrome, then re-run"
            OUT.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(run, ensure_ascii=False, indent=2))
            return 1

        benefits._set_region_south_korea(page)
        found = False
        for q in benefits._search_queries_for_title(GCP_TITLE):
            if benefits._search_benefit(page, q):
                found = True
                run["search_query"] = q
                break
        if not found:
            run["error"] = "gcp_tile_not_found"
            OUT.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(run, ensure_ascii=False, indent=2))
            return 1

        item = benefits._click_request_on_page(page, context, GCP_TITLE)
        run["result"] = item

        popup = None
        for pg in context.pages:
            if "google" in (pg.url or ""):
                popup = pg
                break
        if popup and item.get("human_gate"):
            for _ in range(20):
                popup.wait_for_timeout(3000)
                if "cloud.google.com/startup" in (popup.url or ""):
                    benefits._fill_gcp_partner_form(popup, item)
                    run["result_after_login"] = dict(item)
                    break
                if "challenge/pwd" in (popup.url or ""):
                    item["human_gate"] = "waiting_password"
                    break

        autofill._save_storage_state(context)

    ok = bool(item.get("submit_ok") or (item.get("request_clicked") and not item.get("human_gate")))
    OUT.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
