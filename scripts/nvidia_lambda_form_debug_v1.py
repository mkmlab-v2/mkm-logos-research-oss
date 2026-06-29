#!/usr/bin/env python3
"""Dump Lambda nvidia-inception form fields (CDP debug)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL = "https://lambda.ai/nvidia-inception"


def main() -> int:
    from playwright.sync_api import sync_playwright

    out: dict = {"url": URL, "frames": []}
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = browser.contexts[0].new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(5000)
        for i, fr in enumerate(page.frames):
            block: dict = {"index": i, "url": (fr.url or "")[:200], "inputs": [], "errors": []}
            try:
                for inp in fr.locator("input, textarea, select").all()[:40]:
                    try:
                        if not inp.is_visible(timeout=500):
                            continue
                        block["inputs"].append(
                            {
                                "tag": inp.evaluate("el => el.tagName"),
                                "type": inp.get_attribute("type"),
                                "name": inp.get_attribute("name"),
                                "id": inp.get_attribute("id"),
                                "placeholder": inp.get_attribute("placeholder"),
                                "aria": inp.get_attribute("aria-label"),
                                "value": (inp.input_value(timeout=1000) or "")[:80],
                            }
                        )
                    except Exception:
                        continue
                txt = fr.inner_text("body", timeout=3000) or ""
                for line in txt.splitlines():
                    if any(k in line.lower() for k in ("error", "required", "invalid", "phone")):
                        block["errors"].append(line.strip()[:120])
            except Exception as exc:
                block["frame_error"] = str(exc)[:120]
            if block["inputs"] or block["errors"]:
                out["frames"].append(block)
        page.screenshot(path=str(ROOT / "reports/nvidia_lambda_form_debug_latest.png"), full_page=True)
        page.close()

    path = ROOT / "reports/nvidia_lambda_form_debug_latest.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(path)
    for fr in out["frames"]:
        print(f"frame {fr['index']}: {len(fr['inputs'])} inputs")
        for inp in fr["inputs"]:
            print(f"  {inp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
