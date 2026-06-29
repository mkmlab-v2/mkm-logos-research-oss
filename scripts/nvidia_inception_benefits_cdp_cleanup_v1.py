#!/usr/bin/env python3
"""Close extra CDP Chrome tabs; keep NVIDIA benefits or one partner form."""
from __future__ import annotations

import argparse
import sys

KEEP_HINTS = (
    "lambda.ai/nvidia-inception",
    "nvidia.com/programs/benefits",
    "programs.nvidia.com/phoenix",
    "airtable.com",
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    ap.add_argument("--keep-url-contains", default="")
    args = ap.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("pip install playwright && playwright install chromium", file=sys.stderr)
        return 1

    keep = args.keep_url_contains or ""
    closed = 0
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(args.cdp_url.strip())
        for ctx in browser.contexts:
            pages = list(ctx.pages)
            keeper = None
            for pg in pages:
                url = (pg.url or "").lower()
                if keep and keep.lower() in url:
                    keeper = pg
                    break
                if any(h in url for h in KEEP_HINTS):
                    if keeper is None:
                        keeper = pg
            if keeper is None and pages:
                keeper = pages[0]
            for pg in pages:
                if pg is keeper:
                    try:
                        pg.bring_to_front()
                    except Exception:
                        pass
                    continue
                try:
                    pg.close()
                    closed += 1
                except Exception:
                    pass
    print(f"closed_tabs={closed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
