#!/usr/bin/env python3
"""CDP/headed automation for NGC org account EULA + privacy acceptance (Tier-3 login once).

  py scripts/ngc_org_account_eula_autofill_v1.py --cdp-url http://127.0.0.1:9222 --wait-for-login-sec 180
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
POINTER = ROOT / "reports/nvidia_inception_account_pointer_v1.json"
OUT_REPORT = ROOT / "reports/ngc_org_account_eula_autofill_latest.json"
SCREENSHOT = ROOT / "reports/ngc_org_account_eula_autofill_screenshot.png"
STORAGE = ROOT / "reports/ngc_org_account_storage_state.json"

ACCOUNT_URL = "https://org.ngc.nvidia.com/account"

CLICK_LABELS = (
    "I Agree",
    "I agree",
    "Accept",
    "Accept All",
    "Agree",
    "Sign",
    "Continue",
    "Confirm",
    "Submit",
    "Get Started",
    "Done",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_account_url() -> str:
    if POINTER.is_file():
        try:
            p = json.loads(POINTER.read_text(encoding="utf-8-sig"))
            return p.get("ngc", {}).get("account") or ACCOUNT_URL
        except Exception:
            pass
    return ACCOUNT_URL


def _is_guest(page) -> bool:
    try:
        if page.get_by_text("Welcome Guest", exact=False).count():
            return True
        if page.get_by_text("Sign In", exact=False).count() and page.get_by_text("Welcome Guest", exact=False).count():
            return True
    except Exception:
        pass
    url = page.url.lower()
    return "signin" in url or "login" in url


def _page_has_server_error(page) -> bool:
    try:
        body = page.locator("body").inner_text(timeout=5000)
        if "Internal Server Error" in body:
            return True
    except Exception:
        pass
    return False


def _logged_in_ngc(page) -> bool:
    if _page_has_server_error(page):
        return False
    if _is_guest(page):
        return False
    url = page.url.lower()
    if "org.ngc.nvidia.com" in url and "signin" not in url and "login" not in url:
        return True
    try:
        if page.get_by_text("Welcome Guest", exact=False).count():
            return False
    except Exception:
        pass
    return False


def _wait_login(page, wait_sec: int) -> bool:
    if _logged_in_ngc(page):
        return True
    deadline = time.time() + wait_sec
    while time.time() < deadline:
        if _logged_in_ngc(page):
            return True
        time.sleep(2)
    return _logged_in_ngc(page)


def _click_first_matching(page, labels: tuple[str, ...]) -> str | None:
    for label in labels:
        for factory in (
            lambda l=label: page.get_by_role("button", name=l, exact=False),
            lambda l=label: page.locator("button").filter(has_text=l),
            lambda l=label: page.locator("a").filter(has_text=l),
            lambda l=label: page.get_by_text(l, exact=False),
        ):
            try:
                loc = factory().first
                if loc.count() and loc.is_visible(timeout=1500):
                    loc.scroll_into_view_if_needed(timeout=5000)
                    loc.click(timeout=8000, force=True)
                    page.wait_for_timeout(2000)
                    return label
            except Exception:
                continue
    return None


def _try_checkboxes(page) -> int:
    n = 0
    for sel in (
        "input[type='checkbox']",
        "[role='checkbox']",
    ):
        try:
            for box in page.locator(sel).all()[:12]:
                try:
                    if box.is_visible(timeout=800) and not box.is_checked(timeout=800):
                        box.check(force=True, timeout=3000)
                        n += 1
                        page.wait_for_timeout(300)
                except Exception:
                    continue
        except Exception:
            continue
    return n


def _accept_passes(page, max_rounds: int = 8) -> list[str]:
    actions: list[str] = []
    for _ in range(max_rounds):
        _try_checkboxes(page)
        clicked = _click_first_matching(page, CLICK_LABELS)
        if clicked:
            actions.append(f"click:{clicked}")
            page.wait_for_timeout(2500)
            continue
        break
    return actions


def _probe_ngc_cli() -> dict[str, Any] | None:
    who_script = "/mnt/c/workspace/scripts/wsl/ngc_user_who_json_v1.sh"
    cmd = [
        "wsl.exe",
        "-d",
        "Ubuntu-24.04",
        "--",
        "bash",
        "-c",
        f"sed -i 's/\\r$//' '{who_script}' 2>/dev/null; bash '{who_script}'",
    ]
    try:
        raw = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, timeout=120).strip()
        data = json.loads(raw)
        u = data.get("user") or {}
        return {
            "email": u.get("email"),
            "isActive": u.get("isActive"),
            "hasSignedNvidiaEULA": u.get("hasSignedNvidiaEULA"),
            "hasSignedPrivacyPolicy": u.get("hasSignedPrivacyPolicy"),
        }
    except Exception as exc:
        return {"probe_error": str(exc)[:300]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cdp-url", default="", help="Chrome remote debugging URL")
    ap.add_argument("--wait-for-login-sec", type=int, default=120)
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--skip-cli-probe", action="store_true")
    args = ap.parse_args()

    account_url = _load_account_url()
    run_log: dict[str, Any] = {
        "schema": "ngc_org_account_eula_autofill_v1",
        "generated_at_utc": _utc(),
        "account_url": account_url,
        "actions": [],
        "logged_in": False,
        "eula_automation_ok": False,
        "screenshot": None,
    }

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("pip install playwright && playwright install chromium", file=sys.stderr)
        return 2

    with sync_playwright() as p:
        page = None
        context = None
        if args.cdp_url.strip():
            browser = p.chromium.connect_over_cdp(args.cdp_url.strip())
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.new_page()
        else:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(ROOT / "reports" / "ngc_org_chrome_profile"),
                headless=not args.headed,
                viewport={"width": 1400, "height": 900},
            )
            page = context.pages[0] if context.pages else context.new_page()

        page.goto(account_url, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(2000)
        for attempt in range(3):
            if not _page_has_server_error(page):
                break
            run_log.setdefault("retries", []).append(f"server_error_reload_{attempt + 1}")
            page.reload(wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_timeout(3000)
        if _page_has_server_error(page):
            fallback = "https://ngc.nvidia.com/setup"
            run_log["fallback_url"] = fallback
            page.goto(fallback, wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_timeout(2500)

        if not _logged_in_ngc(page):
            run_log["login_required"] = True
            if args.wait_for_login_sec <= 0:
                run_log["error"] = "not_logged_in — re-run with --wait-for-login-sec 180 after login in browser"
                run_log["page_url"] = page.url
            elif not _wait_login(page, args.wait_for_login_sec):
                run_log["error"] = "login_timeout — log in on org.ngc.nvidia.com in the debug Chrome window"
                run_log["page_url"] = page.url
            else:
                run_log["logged_in"] = True
        else:
            run_log["logged_in"] = True

        if run_log.get("logged_in"):
            if page.url != account_url and "org.ngc.nvidia.com" not in page.url:
                page.goto(account_url, wait_until="domcontentloaded", timeout=120_000)
                page.wait_for_timeout(2000)
            run_log["actions"] = _accept_passes(page)
            try:
                context.storage_state(path=str(STORAGE))
                run_log["storage_state_saved"] = True
            except Exception:
                run_log["storage_state_saved"] = False

        page.screenshot(path=str(SCREENSHOT), full_page=True)
        run_log["screenshot"] = str(SCREENSHOT.relative_to(ROOT)).replace("\\", "/")
        run_log["page_url_final"] = page.url

        if context and not args.cdp_url.strip():
            context.close()

    if not args.skip_cli_probe:
        run_log["ngc_cli_probe_after"] = _probe_ngc_cli()
        probe = run_log["ngc_cli_probe_after"] or {}
        if probe.get("isActive") and probe.get("hasSignedNvidiaEULA") and probe.get("hasSignedPrivacyPolicy"):
            run_log["eula_automation_ok"] = True

    OUT_REPORT.write_text(json.dumps(run_log, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run_log, ensure_ascii=False, indent=2))

    if run_log.get("error"):
        return 1
    if run_log.get("eula_automation_ok"):
        return 0
    if run_log.get("logged_in") and run_log.get("actions"):
        return 0
    return 2 if run_log.get("logged_in") else 1


if __name__ == "__main__":
    raise SystemExit(main())
