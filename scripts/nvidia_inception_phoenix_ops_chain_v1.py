#!/usr/bin/env python3
"""Phoenix ops chain: product patch/wizard submit → Benefits → Innovation Lab request.

  py scripts/nvidia_inception_phoenix_ops_chain_v1.py --cdp-url http://127.0.0.1:9222
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "nvidia_inception_portal_product_autofill_v1",
    ROOT / "scripts" / "nvidia_inception_portal_product_autofill_v1.py",
)
autofill = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(autofill)

OUT_REPORT = ROOT / "reports/nvidia_inception_phoenix_ops_chain_latest.json"
INNOVATION_LAB_BLURB = (
    "MKM seeks GPU credits and technical guidance for TensorRT-LLM / vLLM serving prototypes, "
    "KV-cache efficiency, and Nemotron-scale RAG benchmarks. Tracks: Model Optimizations + "
    "Multimodal RAG. Golden-40 bench: ~47.5% token savings, ~0.89 Jaccard (research harness only). "
    "Website: https://jema-ai.com"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _click_button_text(page, text: str, *, last: bool = False) -> bool:
    loc = page.locator("button").filter(has_text=text)
    if last:
        target = loc.last
    else:
        target = loc.first
    try:
        if target.count() and target.is_visible(timeout=3000):
            target.scroll_into_view_if_needed(timeout=5000)
            target.click(timeout=10_000, force=True)
            page.wait_for_timeout(2000)
            return True
    except Exception:
        pass
    try:
        role = page.get_by_role("button", name=text, exact=True)
        btn = role.last if last else role.first
        if btn.count() and btn.is_visible(timeout=3000):
            btn.scroll_into_view_if_needed(timeout=5000)
            btn.click(timeout=10_000, force=True)
            page.wait_for_timeout(2000)
            return True
    except Exception:
        pass
    return False


def _wizard_to_completion(page, max_steps: int = 12) -> dict[str, Any]:
    log: dict[str, Any] = {"steps": [], "completed": False}
    for i in range(max_steps):
        url_before = page.url
        if _click_button_text(page, "Confirm") or _click_button_text(page, "Finish"):
            page.wait_for_timeout(4000)
            log["steps"].append({"n": i + 1, "action": "confirm", "url": page.url})
            if "add-product" not in page.url:
                log["completed"] = True
                break
            continue
        if _click_button_text(page, "Save") or _click_button_text(page, "Submit"):
            page.wait_for_timeout(4000)
            log["steps"].append({"n": i + 1, "action": "save", "url": page.url})
            if "products" in page.url and "add-product" not in page.url:
                log["completed"] = True
                break
            log["completed"] = True
            break
        if _click_button_text(page, "Next", last=True) or _click_button_text(page, "Next"):
            page.wait_for_load_state("domcontentloaded", timeout=60_000)
            page.wait_for_timeout(1500)
            log["steps"].append({"n": i + 1, "action": "next", "url": page.url})
            if page.url == url_before:
                page.evaluate(
                    """() => {
                    const btns = [...document.querySelectorAll('button')];
                    const n = btns.find(b => b.textContent.trim() === 'Next');
                    if (n) n.click();
                }"""
                )
                page.wait_for_timeout(2000)
            continue
        log["steps"].append({"n": i + 1, "action": "stuck", "url": page.url})
        break
    return log


def _open_sidebar(page, label: str) -> bool:
    for sel in (
        page.get_by_role("link", name=label, exact=False),
        page.get_by_text(label, exact=True),
        page.locator(f"nav a:has-text('{label}')"),
    ):
        try:
            loc = sel.first
            if loc.count() and loc.is_visible(timeout=5000):
                loc.click(timeout=8000)
                page.wait_for_timeout(2000)
                return True
        except Exception:
            continue
    return False


def _benefits_innovation_lab(page, context) -> dict[str, Any]:
    out: dict[str, Any] = {
        "benefits_nav": False,
        "explore_opened": False,
        "innovation_lab_tile": False,
        "request_clicked": False,
        "form_filled": False,
        "url": "",
        "catalog_url": "",
    }
    page.goto("https://programs.nvidia.com/phoenix/benefits", wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(2000)
    out["benefits_nav"] = autofill._logged_in(page)
    out["url"] = page.url

    catalog = page
    explore = page.get_by_text("Explore Benefits", exact=False).first
    try:
        if explore.count() and explore.is_visible(timeout=5000):
            with context.expect_page(timeout=30_000) as new_page_info:
                explore.click(timeout=10_000)
            catalog = new_page_info.value
            catalog.wait_for_load_state("domcontentloaded", timeout=60_000)
            catalog.wait_for_timeout(3000)
            out["explore_opened"] = True
            out["catalog_url"] = catalog.url
    except Exception:
        pass
    if "nvidia.com/programs/benefits" not in catalog.url:
        try:
            catalog.goto(
                "https://www.nvidia.com/programs/benefits/",
                wait_until="domcontentloaded",
                timeout=120_000,
            )
            catalog.wait_for_timeout(4000)
            out["explore_opened"] = True
            out["catalog_url"] = catalog.url
        except Exception:
            out["catalog_url"] = catalog.url

    for search in (
        catalog.get_by_placeholder("Search", exact=False),
        catalog.locator("input[type='search']"),
        catalog.locator("input[placeholder*='Search' i]"),
    ):
        try:
            s = search.first
            if s.count() and s.is_visible(timeout=3000):
                s.fill("Innovation Lab", timeout=5000)
                catalog.keyboard.press("Enter")
                catalog.wait_for_timeout(3000)
                break
        except Exception:
            continue

    for tile in (
        catalog.get_by_text("Innovation Lab", exact=False),
        catalog.get_by_role("link", name="Innovation Lab"),
        catalog.locator("a, button, [role='button']").filter(has_text="Innovation Lab"),
    ):
        try:
            loc = tile.first
            if loc.count() and loc.is_visible(timeout=8000):
                loc.click(timeout=12_000)
                catalog.wait_for_timeout(3000)
                out["innovation_lab_tile"] = True
                break
        except Exception:
            continue

    target = catalog
    for req in (
        catalog.get_by_role("button", name="Request Benefit"),
        catalog.get_by_role("button", name="Request"),
        catalog.get_by_role("link", name="Request Benefit"),
        catalog.get_by_text("Request Benefit", exact=False),
        catalog.locator("a, button").filter(has_text="Request Benefit"),
        catalog.locator("a, button").filter(has_text="Request"),
    ):
        try:
            loc = req.first
            if loc.count() and loc.is_visible(timeout=5000):
                loc.click(timeout=10_000)
                catalog.wait_for_timeout(3000)
                out["request_clicked"] = True
                target = catalog
                break
        except Exception:
            continue

    for ta in target.locator("textarea").all():
        try:
            if ta.is_visible(timeout=2000):
                ta.fill(INNOVATION_LAB_BLURB, timeout=8000)
                out["form_filled"] = True
                break
        except Exception:
            continue

    for btn_label in ("Submit", "Save", "Apply", "Next"):
        if _click_button_text(target, btn_label):
            target.wait_for_timeout(2000)
            break

    out["url"] = target.url
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    ap.add_argument("--wait-for-login-sec", type=int, default=90)
    ap.add_argument("--skip-product", action="store_true")
    ap.add_argument("--skip-benefits", action="store_true")
    ap.add_argument("--patch-only", action="store_true", help="Only patch_only_fields from payload")
    ap.add_argument("--full", action="store_true", help="Fill all payload fields")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("pip install playwright && playwright install chromium", file=sys.stderr)
        return 2

    payload = json.loads(autofill.PAYLOAD.read_text(encoding="utf-8-sig"))
    fields = payload["fields"]
    url = payload.get("portal_url") or "https://programs.nvidia.com/phoenix/products"
    if args.full:
        keys = list(fields.keys())
    elif args.patch_only or payload.get("mode_default") == "patch_only":
        keys = list(payload.get("patch_only_fields") or [])
    else:
        keys = list(fields.keys())

    run: dict[str, Any] = {
        "schema": "nvidia_inception_phoenix_ops_chain_v1",
        "generated_at_utc": _utc(),
        "product": {},
        "wizard": {},
        "benefits": {},
        "screenshots": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(args.cdp_url.strip())
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = None
        best_score = -1
        for pg in context.pages:
            try:
                u = (pg.url or "").lower()
                if "programs.nvidia.com/phoenix" not in u or "login" in u:
                    continue
                text = pg.inner_text("body", timeout=5000) or ""
                if "Welcome to Inception" not in text and "Log Out" not in text:
                    continue
                score = 1
                if u.rstrip("/").endswith("/phoenix"):
                    score += 10
                if "add-product" in u:
                    score += 8
                if score > best_score:
                    best_score = score
                    page = pg
            except Exception:
                continue
        if page is None:
            page = autofill._pick_phoenix_page(context, url)
        if page is None:
            page = context.new_page()
            autofill._inject_storage_state(context)
            page.goto("https://programs.nvidia.com/phoenix/", wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_timeout(3000)
        else:
            page.bring_to_front()
            page.wait_for_timeout(1000)

        if not autofill._logged_in(page):
            try:
                body = page.inner_text("body", timeout=5000) or ""
                if "Welcome to Inception" in body or "Log Out" in body:
                    pass
                elif not autofill._wait_past_login(page, args.wait_for_login_sec):
                    run["error"] = "login_timeout"
                    run["page_url"] = page.url
                    OUT_REPORT.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
                    print(json.dumps(run, ensure_ascii=False, indent=2))
                    return 1
            except Exception:
                if not autofill._wait_past_login(page, args.wait_for_login_sec):
                    run["error"] = "login_timeout"
                    run["page_url"] = page.url
                    OUT_REPORT.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
                    print(json.dumps(run, ensure_ascii=False, indent=2))
                    return 1

        if not args.skip_product:
            run["product"]["edit_opened"] = autofill._open_product_from_home_cta(page)
            if not run["product"]["edit_opened"]:
                run["product"]["edit_opened"] = autofill._open_product_edit_direct(page, args.wait_for_login_sec)
            if not run["product"]["edit_opened"]:
                run["product"]["edit_opened"] = autofill._open_edit_form(page)
            page.wait_for_timeout(2000)
            autofill._advance_wizard_if_needed(page)
            run["product"]["fields"] = (
                autofill._apply_fields(page, fields, keys) if run["product"]["edit_opened"] else {}
            )
            if run["product"]["edit_opened"] and run["product"]["fields"]:
                autofill._advance_wizard_if_needed(page)
                run["product"]["saved"] = autofill._submit_product_wizard(page)
            shot1 = ROOT / "reports/nvidia_inception_ops_chain_product.png"
            if autofill._safe_screenshot(page, shot1):
                run["screenshots"].append(str(shot1.relative_to(ROOT)).replace("\\", "/"))
            run["wizard"] = _wizard_to_completion(page)
            shot2 = ROOT / "reports/nvidia_inception_ops_chain_after_wizard.png"
            if autofill._safe_screenshot(page, shot2):
                run["screenshots"].append(str(shot2.relative_to(ROOT)).replace("\\", "/"))

        if not args.skip_benefits:
            run["benefits"] = _benefits_innovation_lab(page, context)
            shot3 = ROOT / "reports/nvidia_inception_ops_chain_benefits.png"
            if autofill._safe_screenshot(page, shot3):
                run["screenshots"].append(str(shot3.relative_to(ROOT)).replace("\\", "/"))

    OUT_REPORT.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    wiz = run.get("wizard", {})
    ben = run.get("benefits", {})
    ok = (
        wiz.get("completed")
        or any(s.get("action") == "confirm" for s in wiz.get("steps", []))
        or ben.get("explore_opened")
        or ben.get("innovation_lab_tile")
        or ben.get("request_clicked")
        or sum(1 for v in run.get("product", {}).get("fields", {}).values() if v) >= 1
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
