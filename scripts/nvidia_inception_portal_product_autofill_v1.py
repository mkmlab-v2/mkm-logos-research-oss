#!/usr/bin/env python3
"""Playwright autofill for NVIDIA Inception Phoenix product form (Tier-3 login: human once).

Usage (first time — log in when browser opens, then script continues):
  py scripts/nvidia_inception_portal_product_autofill_v1.py --headed --wait-for-login-sec 300

Reuse session next time:
  py scripts/nvidia_inception_portal_product_autofill_v1.py --headed

Attach to your already-logged-in Chrome (start Chrome with remote debugging):
  chrome.exe --remote-debugging-port=9222
  py scripts/nvidia_inception_portal_product_autofill_v1.py --cdp-url http://127.0.0.1:9222
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PAYLOAD = ROOT / "reports/nvidia_inception_portal_autofill_payload_v1.json"
STORAGE = ROOT / "reports/nvidia_inception_portal_storage_state.json"
# Same user-data-dir as Start-ChromeForNvidiaInceptionAutofill_v1.ps1
PROFILE_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "NvidiaInceptionAutofillChrome"
OUT_REPORT = ROOT / "reports/nvidia_inception_portal_autofill_run_latest.json"


def _safe_screenshot(page, path: Path) -> bool:
    try:
        page.screenshot(path=str(path), full_page=False, timeout=20_000)
        return True
    except Exception:
        try:
            page.screenshot(path=str(path), full_page=True, timeout=45_000)
            return True
        except Exception:
            return False


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _save_storage_state(context: Any) -> None:
    try:
        context.storage_state(path=str(STORAGE))
    except Exception:
        pass


def _pick_phoenix_page(context: Any, url: str) -> Any:
    """Prefer an already-logged-in Phoenix tab (CDP attach)."""
    scored: list[tuple[int, Any]] = []
    for pg in context.pages:
        try:
            u = pg.url.lower()
            if "programs.nvidia.com/phoenix" not in u or "login" in u or "signin" in u:
                continue
            score = 1
            if u.rstrip("/").endswith("/phoenix") or "/phoenix/" in u:
                score += 2
            if "products" in u:
                score += 4
            if "add-product" in u:
                score += 5
            if "profile" in u:
                score += 3
            scored.append((score, pg))
        except Exception:
            continue
    if scored:
        return max(scored, key=lambda item: item[0])[1]
    for pg in context.pages:
        try:
            if "programs.nvidia.com" in pg.url.lower():
                return pg
        except Exception:
            continue
    if context.pages:
        return context.pages[0]
    return context.new_page()


def _inject_storage_state(context: Any) -> bool:
    """Restore saved Phoenix cookies (CDP or persistent context)."""
    if not STORAGE.is_file():
        return False
    try:
        state = json.loads(STORAGE.read_text(encoding="utf-8-sig"))
        cookies = state.get("cookies") or []
        if cookies:
            context.add_cookies(cookies)
            return True
    except Exception:
        pass
    return False


def _fill_if_visible(page, selectors: list[str], value: str) -> bool:
    for sel in selectors:
        loc = page.locator(sel).first
        if loc.count() == 0:
            continue
        try:
            if loc.is_visible(timeout=2000):
                loc.click(timeout=3000)
                loc.fill(value, timeout=5000)
                return True
        except Exception:
            continue
    return False


def _select_if_visible(page, selectors: list[str], label: str) -> bool:
    for sel in selectors:
        loc = page.locator(sel).first
        if loc.count() == 0:
            continue
        try:
            if loc.is_visible(timeout=2000):
                loc.select_option(label=label, timeout=5000)
                return True
        except Exception:
            try:
                loc.select_option(value=label, timeout=5000)
                return True
            except Exception:
                continue
    return False


def _clear_and_fill(loc, value: str) -> None:
    loc.click(timeout=3000)
    loc.press("Control+A", timeout=2000)
    loc.press("Backspace", timeout=2000)
    loc.fill(str(value), timeout=8000)


def _fill_tag_combobox(page, label_fragments: tuple[str, ...], value: str) -> bool:
    """Salesforce-style tag pickers: type each token and press Enter."""
    tags = [t.strip() for t in str(value).replace(",", ";").split(";") if t.strip()]
    if not tags:
        return False
    loc = None
    for frag in label_fragments:
        try:
            candidate = page.get_by_label(frag, exact=False).first
            if candidate.count() and candidate.is_visible(timeout=2500):
                loc = candidate
                break
        except Exception:
            continue
    if loc is None:
        for frag in label_fragments:
            try:
                q = page.get_by_text(frag, exact=False).first
                if not q.count():
                    continue
                container = q.locator("xpath=ancestor::*[contains(@class,'form-element') or contains(@class,'slds-form')][1]")
                candidate = container.locator("input[type='text'], input:not([type='hidden'])").first
                if candidate.count() and candidate.is_visible(timeout=2000):
                    loc = candidate
                    break
            except Exception:
                continue
    if loc is None:
        return False
    try:
        loc.click(timeout=3000)
        for tag in tags:
            loc.fill(tag, timeout=5000)
            page.keyboard.press("Enter")
            page.wait_for_timeout(500)
        return True
    except Exception:
        return False


def _select_combobox(page, label_fragment: str, option_text: str) -> bool:
    try:
        combo = page.get_by_label(label_fragment, exact=False).first
        if not combo.count():
            return False
        combo.click(timeout=5000)
        page.wait_for_timeout(500)
        opt = page.get_by_role("option", name=str(option_text), exact=False).first
        if opt.count() and opt.is_visible(timeout=3000):
            opt.click(timeout=5000)
            return True
        page.get_by_text(str(option_text), exact=True).first.click(timeout=5000)
        return True
    except Exception:
        try:
            page.get_by_label(label_fragment, exact=False).select_option(label=str(option_text), timeout=5000)
            return True
        except Exception:
            return False


def _submit_product_wizard(page) -> bool:
    """Phoenix add/edit product is multi-step (Back / Next / Confirm); Save on last step."""
    for _ in range(12):
        for sel in (
            page.get_by_role("button", name="Save", exact=True),
            page.get_by_role("button", name="Submit", exact=False),
            page.locator('button:has-text("Save")'),
            page.locator('button:has-text("Submit")'),
            page.locator('input[type="submit"][value*="Save" i]'),
        ):
            try:
                btn = sel.first
                if btn.count() and btn.is_visible(timeout=2000):
                    btn.scroll_into_view_if_needed(timeout=5000)
                    btn.click(timeout=8000)
                    page.wait_for_timeout(3000)
                    return True
            except Exception:
                continue
        clicked_advance = False
        for nxt_sel in (
            page.get_by_role("button", name="Next", exact=True),
            page.get_by_role("button", name="Confirm", exact=True),
            page.locator("button.slds-button_brand").filter(has_text="Next"),
            page.locator("button.slds-button_brand").filter(has_text="Confirm"),
            page.locator("footer button").filter(has_text="Next"),
            page.locator("footer button").filter(has_text="Confirm"),
            page.locator("button").filter(has_text="Next"),
            page.locator("button").filter(has_text="Confirm"),
        ):
            try:
                nxt = nxt_sel.first
                if nxt.count() and nxt.is_visible(timeout=2000):
                    nxt.scroll_into_view_if_needed(timeout=5000)
                    nxt.click(timeout=8000, force=True)
                    page.wait_for_timeout(2500)
                    clicked_advance = True
                    break
            except Exception:
                continue
        if clicked_advance:
            continue
        break
    return False


def _click_first(page, selectors: list[str]) -> bool:
    for sel in selectors:
        loc = page.locator(sel).first
        if loc.count() == 0:
            continue
        try:
            if loc.is_visible(timeout=2000):
                loc.click(timeout=5000)
                return True
        except Exception:
            continue
    return False


def _logged_in(page) -> bool:
    url = page.url.lower()
    if "login" in url or "signin" in url or "auth" in url and "phoenix" not in url:
        return False
    if "phoenix" in url or "programs.nvidia.com" in url:
        return True
    try:
        if page.get_by_text("Welcome to Inception", exact=False).count() > 0:
            return True
        if page.locator("table").count() > 0:
            return True
    except Exception:
        pass
    return "login" not in url and "signin" not in url


def _wait_past_login(page, wait_sec: int) -> bool:
    if _logged_in(page):
        return True
    deadline = time.time() + wait_sec
    while time.time() < deadline:
        if _logged_in(page):
            return True
        time.sleep(2)
    return _logged_in(page)


def _try_phoenix_email_gate(page) -> bool:
    """On Inception email gate, pre-fill business email from pointer SSOT."""
    pointer_path = ROOT / "reports/nvidia_inception_account_pointer_v1.json"
    if not pointer_path.is_file():
        return False
    try:
        pointer = json.loads(pointer_path.read_text(encoding="utf-8-sig"))
        email = (
            pointer.get("inception", {}).get("primary_login_email")
            or pointer.get("ngc", {}).get("cli_email_last_seen")
            or ""
        )
        if not email:
            return False
        for loc in (
            page.get_by_placeholder("Enter your business email", exact=False),
            page.get_by_label("business email", exact=False),
            page.locator("input[type='email']"),
            page.locator("input[name*='email' i]"),
        ):
            try:
                field = loc.first
                if field.count() and field.is_visible(timeout=3000):
                    field.fill(email, timeout=5000)
                    for btn in (
                        page.get_by_role("button", name="Sign Up / Login", exact=False),
                        page.get_by_role("button", name="Login", exact=False),
                        page.locator("button").filter(has_text="Sign Up"),
                    ):
                        try:
                            b = btn.first
                            if b.count() and b.is_visible(timeout=2000):
                                b.click(timeout=5000)
                                page.wait_for_timeout(3000)
                                return True
                        except Exception:
                            continue
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def _advance_wizard_if_needed(page, max_steps: int = 6) -> None:
    """Click Next until NVIDIA tech / description fields appear (multi-step add-product)."""
    for _ in range(max_steps):
        try:
            if page.get_by_label("Which NVIDIA technologies are currently used", exact=False).first.is_visible(
                timeout=1500
            ):
                return
            if page.get_by_label("Technical Details", exact=False).first.is_visible(timeout=1500):
                return
            if page.get_by_label("Describe your product", exact=False).first.is_visible(timeout=1500):
                return
        except Exception:
            pass
        if not _click_first(
            page,
            [
                'button:has-text("Next")',
                '[role="button"]:has-text("Next")',
            ],
        ):
            break
        page.wait_for_timeout(1500)


PRODUCT_EDIT_URL = (
    "https://programs.nvidia.com/phoenix/products/add-product?id=aDVVv000000CovVOAS"
)
PRODUCTS_URLS = (
    "https://programs.nvidia.com/phoenix/products",
    "https://programs.nvidia.com/phoenix/profile?program=inception",
)


def _form_surface_visible(page) -> bool:
    try:
        if page.get_by_label("Product/Service Name", exact=False).first.is_visible(timeout=3000):
            return True
    except Exception:
        pass
    try:
        if page.locator("textarea").first.is_visible(timeout=2000):
            return True
    except Exception:
        pass
    return False


def _recover_phoenix_login(page, wait_sec: int) -> bool:
    if _logged_in(page) and "login" not in page.url.lower():
        return True
    _try_phoenix_email_gate(page)
    if wait_sec > 0:
        return _wait_past_login(page, wait_sec)
    return _logged_in(page) and "login" not in page.url.lower()


def _open_product_from_home_cta(page) -> bool:
    """Use Inception home CTA — avoids /products login redirect in some sessions."""
    try:
        if "programs.nvidia.com/phoenix" not in (page.url or "").lower() or "login" in (page.url or "").lower():
            page.goto("https://programs.nvidia.com/phoenix/", wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_timeout(2500)
    except Exception:
        pass
    for label in ("Add Product Details", "Products"):
        try:
            loc = page.get_by_role("link", name=label, exact=False).first
            if loc.count() and loc.is_visible(timeout=3000):
                loc.click(timeout=8000)
                page.wait_for_timeout(3500)
                if _form_surface_visible(page) or "add-product" in (page.url or "").lower():
                    return True
        except Exception:
            continue
    try:
        loc = page.get_by_text("Add Product Details", exact=False).first
        if loc.count() and loc.is_visible(timeout=2000):
            loc.click(timeout=8000)
            page.wait_for_timeout(3500)
            return _form_surface_visible(page) or "add-product" in (page.url or "").lower()
    except Exception:
        pass
    return False


def _open_product_edit_direct(page, wait_sec: int = 0) -> bool:
    """Deep-link to known product id; recover login once if session expired."""
    edit_url = PRODUCT_EDIT_URL
    for attempt in range(2):
        try:
            page.goto(edit_url, wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_timeout(2500)
        except Exception:
            continue
        if "login" in page.url.lower() or not _logged_in(page):
            if attempt == 0 and wait_sec > 0:
                if _recover_phoenix_login(page, wait_sec):
                    continue
            return False
        if _form_surface_visible(page):
            return True
        _advance_wizard_if_needed(page)
        if _form_surface_visible(page):
            return True
    return _form_surface_visible(page)


def _ensure_products_surface(page, primary_url: str) -> str:
    """Navigate to a products list / profile surface (logged-in)."""
    candidates = [primary_url, *PRODUCTS_URLS]
    seen: set[str] = set()
    for target in candidates:
        if not target or target in seen:
            continue
        seen.add(target)
        try:
            if target not in page.url:
                page.goto(target, wait_until="domcontentloaded", timeout=120_000)
                page.wait_for_timeout(2000)
            if _logged_in(page):
                return page.url
        except Exception:
            continue
    return page.url


def _product_already_listed(page, name_fragment: str = "MKM") -> bool:
    try:
        _ensure_products_surface(page, PRODUCTS_URLS[0])
        page.wait_for_timeout(1500)
        row = page.locator("table tbody tr").filter(has_text=name_fragment).first
        return row.count() > 0 and row.is_visible(timeout=5000)
    except Exception:
        return False


def _open_edit_form(page) -> bool:
    _ensure_products_surface(page, PRODUCTS_URLS[0])
    # Known product id from prior run (edit wizard deep-link)
    for deep in (
        "https://programs.nvidia.com/phoenix/products/add-product?id=aDVVv000000CovVOAS",
        "https://programs.nvidia.com/phoenix/products/add-product",
    ):
        try:
            page.goto(deep, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(2500)
            if page.get_by_label("Product/Service Name", exact=False).first.is_visible(timeout=5000):
                return True
            if page.locator("textarea").first.is_visible(timeout=3000):
                return True
        except Exception:
            continue

    _ensure_products_surface(page, PRODUCTS_URLS[0])
    for wait_sel in ("table", "table tbody tr", "[href*='add-product']", "text=Add Product"):
        try:
            page.wait_for_selector(wait_sel, timeout=15_000)
            break
        except Exception:
            continue

    for edit_sel in (
        page.locator("table tbody tr").filter(has_text="MKM").locator("td").first,
        page.locator("table tbody tr").first.locator("td").first,
        page.get_by_role("link", name="Edit"),
        page.locator("[title*='Edit' i], [aria-label*='Edit' i]").first,
    ):
        try:
            if hasattr(edit_sel, "count") and edit_sel.count() == 0:
                continue
            if edit_sel.is_visible(timeout=3000):
                edit_sel.click(timeout=8000)
                page.wait_for_timeout(2500)
                if "add-product" in page.url or page.locator("textarea").count():
                    return True
        except Exception:
            continue

    row = page.locator("table tbody tr").filter(has_text="MKM").first
    if row.count() == 0:
        row = page.locator("table tbody tr").first
    if row.count() == 0:
        return False
    edit_cell = row.locator("td").first
    for sel in ("a", "button", "[role='button']", "svg", "img"):
        loc = edit_cell.locator(sel).first
        try:
            if loc.count() and loc.is_visible(timeout=3000):
                loc.click(timeout=8000)
                page.wait_for_load_state("domcontentloaded", timeout=60_000)
                page.wait_for_timeout(2000)
                return True
        except Exception:
            continue
    try:
        edit_cell.click(timeout=8000)
        page.wait_for_timeout(2000)
        return True
    except Exception:
        return False


def _apply_fields(page, fields: dict[str, Any], keys: list[str]) -> dict[str, bool]:
    results: dict[str, bool] = {}
    label_map = {
        "product_name": (["input[name*='product' i][name*='name' i]", "input[id*='product' i][id*='name' i]"], None),
        "product_webpage": (["input[name*='web' i]", "input[type='url']"], None),
        "product_type": ([], "product_type"),
        "development_stage": ([], "development_stage"),
        "value_proposition": (["textarea"], "value_proposition"),
        "technical_details": (["textarea"], "technical_details"),
        "gpu_acceleration": ([], "gpu_acceleration"),
        "nvidia_technologies_used": (["input", "textarea"], "nvidia_used"),
        "nvidia_technologies_considering": (["input", "textarea"], "nvidia_considering"),
        "non_nvidia_technologies": (["input", "textarea"], "non_nvidia"),
    }

    for key in keys:
        val = fields.get(key)
        if val is None:
            results[key] = False
            continue
        if key == "product_type":
            results[key] = _select_combobox(page, "Product/Service Type", str(val))
            continue
        if key == "development_stage":
            results[key] = _select_combobox(page, "Development Stage", str(val))
            continue
        if key == "gpu_acceleration":
            try:
                page.get_by_label("accelerated by NVIDIA", exact=False).get_by_text(str(val), exact=True).click(timeout=5000)
                page.keyboard.press("Escape")
                page.wait_for_timeout(400)
                results[key] = True
            except Exception:
                results[key] = False
            continue
        if key == "uses_nvidia_technologies" or key == "considering_nvidia":
            results[key] = True
            continue
        if key == "value_proposition":
            loc = page.get_by_label("Describe your product", exact=False).first
            if loc.count() and loc.is_visible():
                loc.fill(str(val))
                results[key] = True
            else:
                results[key] = _fill_if_visible(page, ["textarea"], str(val))
            continue
        if key == "technical_details":
            loc = page.get_by_label("Technical Details", exact=False).first
            if loc.count() and loc.is_visible():
                _clear_and_fill(loc, str(val))
                results[key] = True
            else:
                results[key] = False
            continue
        if key == "nvidia_technologies_used":
            _advance_wizard_if_needed(page)
            results[key] = _fill_tag_combobox(
                page,
                (
                    "Which NVIDIA technologies are currently used",
                    "NVIDIA technologies are currently used",
                    "currently used",
                ),
                str(val),
            )
            continue
        if key == "nvidia_technologies_considering":
            _advance_wizard_if_needed(page)
            results[key] = _fill_tag_combobox(
                page,
                (
                    "Which NVIDIA technologies are being considered",
                    "NVIDIA technologies are being considered",
                    "being considered",
                ),
                str(val),
            )
            continue
        if key == "non_nvidia_technologies":
            results[key] = _fill_tag_combobox(
                page,
                ("non-NVIDIA", "non NVIDIA", "Non-NVIDIA"),
                str(val),
            )
            continue
        if key == "product_name":
            try:
                loc = page.get_by_label("Product/Service Name", exact=False).first
                loc.click(timeout=3000)
                loc.fill("", timeout=3000)
                loc.fill(str(val), timeout=5000)
                results[key] = True
            except Exception:
                results[key] = False
            continue
        if key == "product_webpage":
            loc = page.get_by_label("Product/Service Webpage", exact=False).first
            if loc.count():
                loc.fill(str(val))
                results[key] = True
            else:
                results[key] = False
            continue
        results[key] = False
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--payload", type=Path, default=PAYLOAD)
    ap.add_argument("--headed", action="store_true", help="Show browser window")
    ap.add_argument("--wait-for-login-sec", type=int, default=0)
    ap.add_argument("--cdp-url", default="", help="Connect to Chrome remote debugging")
    ap.add_argument("--patch-only", action="store_true", help="Only patch SSOT technology fields")
    ap.add_argument("--full", action="store_true", help="Fill all fields from payload")
    ap.add_argument("--skip-if-saved", action="store_true", help="Exit 0 if MKM product row already on portal")
    ap.add_argument("--no-save", action="store_true", help="Fill only, do not click Save")
    args = ap.parse_args()

    payload = json.loads(args.payload.read_text(encoding="utf-8-sig"))
    fields = payload["fields"]
    if args.patch_only or (not args.full and payload.get("mode_default") == "patch_only"):
        keys = list(payload.get("patch_only_fields") or [])
    else:
        keys = list(fields.keys())

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Install: pip install playwright && playwright install chromium", file=sys.stderr)
        return 2

    url = payload.get("portal_url") or "https://programs.nvidia.com/phoenix/products"
    run_log: dict[str, Any] = {
        "schema": "nvidia_inception_portal_autofill_run_v1",
        "generated_at_utc": _utc(),
        "portal_url": url,
        "mode": "patch_only" if args.patch_only else "full",
        "field_results": {},
        "edit_form_opened": False,
        "saved": False,
        "screenshot": None,
    }

    with sync_playwright() as p:
        browser = None
        context = None
        page = None

        if args.cdp_url.strip():
            browser = p.chromium.connect_over_cdp(args.cdp_url.strip())
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = _pick_phoenix_page(context, url)
            if page is None:
                page = context.new_page()
            on_phoenix = "programs.nvidia.com/phoenix" in (page.url or "").lower()
            if not _logged_in(page) or not on_phoenix:
                _inject_storage_state(context)
                if not on_phoenix or not _logged_in(page):
                    page.goto(url, wait_until="domcontentloaded", timeout=120_000)
            elif "products" not in page.url.lower():
                try:
                    page.goto(PRODUCTS_URLS[0], wait_until="domcontentloaded", timeout=120_000)
                    page.wait_for_timeout(2000)
                except Exception:
                    pass
        else:
            PROFILE_DIR.mkdir(parents=True, exist_ok=True)
            profile_has_session = (PROFILE_DIR / "Default" / "Cookies").exists()
            context = p.chromium.launch_persistent_context(
                str(PROFILE_DIR),
                headless=not args.headed,
                viewport={"width": 1400, "height": 900},
            )
            browser = None
            page = _pick_phoenix_page(context, url)
            if not profile_has_session:
                _inject_storage_state(context)
            if not _logged_in(page):
                page.goto(url, wait_until="domcontentloaded", timeout=120_000)
            elif "products" not in page.url.lower():
                page.goto(url, wait_until="domcontentloaded", timeout=120_000)

        wait_sec = args.wait_for_login_sec
        if not _logged_in(page) and wait_sec <= 0 and args.cdp_url.strip():
            wait_sec = 120
        if not _logged_in(page):
            if "login" in page.url.lower() or page.get_by_placeholder("Enter your business email", exact=False).count():
                run_log["phoenix_email_prefill"] = _try_phoenix_email_gate(page)
            if wait_sec <= 0:
                run_log["error"] = (
                    "not_logged_in — re-run with --headed --wait-for-login-sec 300 "
                    "or --cdp-url http://127.0.0.1:9222 after starting Chrome with remote debugging"
                )
                run_log["page_url"] = page.url
                OUT_REPORT.write_text(json.dumps(run_log, indent=2) + "\n", encoding="utf-8")
                if context and not args.cdp_url:
                    context.close()
                return 1
            if not _wait_past_login(page, wait_sec):
                run_log["error"] = "login_timeout — log in in the opened browser, then re-run (profile saved)"
                run_log["page_url"] = page.url
                OUT_REPORT.write_text(json.dumps(run_log, indent=2) + "\n", encoding="utf-8")
                if context and not args.cdp_url:
                    context.close()
                return 1

        try:
            _save_storage_state(context)
            run_log["storage_state_saved"] = True
        except Exception:
            run_log["storage_state_saved"] = False

        if args.skip_if_saved and _product_already_listed(page):
            run_log["skipped"] = "product_already_on_portal"
            run_log["saved"] = True
            run_log["edit_form_opened"] = False
            OUT_REPORT.write_text(json.dumps(run_log, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(run_log, ensure_ascii=False, indent=2))
            if context and not args.cdp_url:
                context.close()
            return 0

        run_log["edit_form_opened"] = False
        try:
            run_log["edit_form_opened"] = _open_product_edit_direct(page, wait_sec)
            if not run_log["edit_form_opened"]:
                run_log["edit_form_opened"] = _open_edit_form(page)
        except Exception as exc:
            run_log["edit_form_error"] = str(exc)[:500]
        if not run_log["edit_form_opened"]:
            if "login" in page.url.lower():
                run_log.setdefault(
                    "error",
                    "session_expired — log in once in NvidiaInceptionAutofillChrome (headed run), then re-run",
                )
            else:
                run_log.setdefault("error", "edit_form_not_opened — check screenshot / storage_state")
        page.wait_for_timeout(2000)
        _advance_wizard_if_needed(page)
        run_log["field_results"] = _apply_fields(page, fields, keys) if run_log["edit_form_opened"] else {}
        run_log["page_url_after_edit"] = page.url
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
        except Exception:
            pass

        shot = ROOT / "reports/nvidia_inception_portal_autofill_screenshot.png"
        if _safe_screenshot(page, shot):
            run_log["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")

        if not args.no_save:
            run_log["saved"] = _submit_product_wizard(page)
            if run_log["saved"]:
                page.wait_for_timeout(3000)
                _safe_screenshot(page, shot)

        if browser and not args.cdp_url:
            browser.close()
        elif context and not args.cdp_url:
            context.close()

    OUT_REPORT.write_text(json.dumps(run_log, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run_log, ensure_ascii=False, indent=2))
    ok_count = sum(1 for v in run_log["field_results"].values() if v)
    return 0 if ok_count >= 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
