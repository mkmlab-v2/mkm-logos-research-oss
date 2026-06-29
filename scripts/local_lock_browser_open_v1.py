#!/usr/bin/env python3
"""P1.5 Commander Vault browser helper — identity plane only; never receives secrets."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

DEFAULT_EMAIL_SELECTORS = (
    'input[type="email"], input[name="email"], input[name="username"], '
    'input[autocomplete="username"], [placeholder*="Email" i], [placeholder*="email" i]'
)
DEFAULT_PASSWORD_SELECTOR = 'input[type="password"]'


def _appdata_mkm() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not set (Windows-only helper).")
    return Path(appdata) / "MKM"


def _profile_dir(key: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in key)
    return _appdata_mkm() / "browser_profiles" / safe


def _load_meta(*, meta_json: str | None, meta_file: Path | None) -> dict[str, Any]:
    if meta_file is not None:
        raw = meta_file.read_text(encoding="utf-8")
    elif meta_json:
        raw = meta_json
    else:
        raise ValueError("Missing metadata payload (--meta-file or positional JSON).")
    meta = json.loads(raw)
    if not isinstance(meta, dict):
        raise ValueError("Metadata payload must be a JSON object.")
    for field in ("key", "login_url", "email"):
        if not meta.get(field):
            raise ValueError(f"Missing required identity field: {field}")
    return meta


def _redacted_summary(meta: dict[str, Any]) -> dict[str, Any]:
    autofill = meta.get("autofill") or {}
    return {
        "schema": "local_lock_browser_open_v1",
        "key": meta.get("key"),
        "login_url": meta.get("login_url"),
        "email_present": bool(meta.get("email")),
        "browser_tier": meta.get("browser_tier", 3),
        "autofill_mode": autofill.get("mode", "email_only"),
        "research_only": True,
        "send_gate": "HOLD",
        "secret_plane": "not_passed",
    }


def _fill_email_react_safe(page: Any, selector: str, email: str) -> None:
    loc = page.locator(selector).first
    loc.wait_for(state="visible", timeout=8000)
    loc.click()
    try:
        loc.fill("")
        loc.fill(email)
        current = loc.input_value()
        if current != email:
            raise ValueError("fill did not stick")
    except Exception:
        loc.click()
        loc.press_sequentially(email, delay=40)


def run_semi_automated_login(meta: dict[str, Any]) -> int:
    from playwright.sync_api import sync_playwright

    key = str(meta["key"])
    url = str(meta["login_url"])
    email = str(meta["email"])
    autofill = meta.get("autofill") or {}
    mode = autofill.get("mode", "email_only")
    email_sel = autofill.get("email_selector") or DEFAULT_EMAIL_SELECTORS
    pass_sel = autofill.get("password_selector") or DEFAULT_PASSWORD_SELECTOR

    profile = _profile_dir(key)
    profile.mkdir(parents=True, exist_ok=True)

    print(f"[Vault-Browser] Launching isolated profile for: {key}")
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(url, wait_until="domcontentloaded")

        if mode == "email_only":
            try:
                _fill_email_react_safe(page, email_sel, email)
                print("[Vault-Browser] Identity email autofilled (password not touched).")
                if page.locator(pass_sel).count() > 0:
                    page.locator(pass_sel).first.focus()
            except Exception as exc:  # noqa: BLE001
                print(
                    "[Vault-Browser] Autofill selector miss; use clipboard email. "
                    f"detail={type(exc).__name__}"
                )
        elif mode == "clipboard_email":
            print("[Vault-Browser] clipboard_email mode — email should be on clipboard from PS1.")
            if page.locator(pass_sel).count() > 0:
                page.locator(pass_sel).first.focus()
        else:
            print("[Vault-Browser] autofill.mode=none — navigation only.")

        print("[Vault-Browser] Handover to commander. Close the window to end.")
        if context.pages:
            context.pages[0].wait_for_event("close")
        context.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="LocalLock P1.5 browser open (identity plane only).")
    parser.add_argument("meta_json", nargs="?", help="JSON metadata string (identity fields only).")
    parser.add_argument("--meta-file", type=Path, help="Path to identity JSON payload.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate payload and print redacted summary without launching a browser.",
    )
    args = parser.parse_args()

    try:
        meta = _load_meta(meta_json=args.meta_json, meta_file=args.meta_file)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(json.dumps(_redacted_summary(meta), ensure_ascii=False))
        return 0

    try:
        return run_semi_automated_login(meta)
    except ImportError:
        print(
            "Error: playwright is not installed. Run: py -m pip install playwright && py -m playwright install chrome",
            file=sys.stderr,
        )
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
