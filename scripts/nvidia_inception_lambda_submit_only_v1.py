#!/usr/bin/env python3
"""CDP: Lambda nvidia-inception 탭만 열고 제출 시도."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "benefits",
    ROOT / "scripts" / "nvidia_inception_benefits_catalog_request_v1.py",
)
mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(mod)

LAMBDA_URL = "https://lambda.ai/nvidia-inception"


def main() -> int:
    from datetime import datetime, timezone

    from playwright.sync_api import sync_playwright

    out: dict = {
        "schema": "nvidia_lambda_submit_only_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "url": "",
        "submit_ok": False,
    }
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = None
        for pg in ctx.pages:
            if "lambda.ai" in (pg.url or ""):
                page = pg
                break
        if page is None:
            page = ctx.new_page()
        page.goto(LAMBDA_URL, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(4000)
        page.bring_to_front()
        out["url"] = page.url
        item: dict = {"title": "$7,500 in Lambda Cloud Credits", "request_clicked": True, "popup_url": page.url}
        mod._fill_lambda_benefit_form(page, item)
        out.update(item)
        shot = ROOT / "reports/nvidia_lambda_submit_only_latest.png"
        try:
            page.screenshot(path=str(shot), timeout=15_000)
            out["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
        except Exception:
            pass
    path = ROOT / "reports/nvidia_lambda_submit_only_latest.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("submit_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
