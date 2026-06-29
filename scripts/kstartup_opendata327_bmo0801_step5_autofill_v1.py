"""BMO0801 STEP05 인력정보 only — OpenData 327 과제 20460558."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "kstartup_opendata327_bmo0801_step5_autofill_latest.json"

from kstartup_opendata327_bmo0801_autofill_v1 import (  # noqa: E402
    _fill_step5,
    _open_task_edit,
    _pick_pms_page,
    _unlock_page_for_user,
    _wait_pms_logged_in,
)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cdp-url", default="http://127.0.0.1:9223")
    ap.add_argument("--task-id", default="20460558")
    ap.add_argument("--wait-for-login-sec", type=int, default=30)
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("pip install playwright", file=sys.stderr)
        return 2

    log: dict = {
        "schema": "kstartup_opendata327_bmo0801_step5_autofill_v1",
        "generated_at_utc": _utc(),
        "task_id": args.task_id,
        "boundary_ack": "no_final_submit — human 제출완료 only",
    }

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(args.cdp_url.strip(), timeout=15000)
        page = _pick_pms_page(browser.contexts[0])
        if not _wait_pms_logged_in(page, args.wait_for_login_sec):
            log["error"] = "login_timeout"
            OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return 1
        log["open"] = _open_task_edit(page, args.task_id.strip())
        if not log["open"].get("ok"):
            OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(log, ensure_ascii=False, indent=2))
            return 1
        log["unlock"] = _unlock_page_for_user(page)
        log["step5"] = _fill_step5(page)
        try:
            page.screenshot(
                path=str(ROOT / "reports" / "kstartup_opendata327_bmo0801_step5_autofill_latest.png"),
                full_page=False,
            )
            log["screenshot"] = "reports/kstartup_opendata327_bmo0801_step5_autofill_latest.png"
        except Exception:
            pass
        ok = bool(log["step5"].get("ok")) and bool(log["step5"].get("saved"))
        OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(log, ensure_ascii=False, indent=2))
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
