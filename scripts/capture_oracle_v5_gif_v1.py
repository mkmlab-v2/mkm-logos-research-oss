#!/usr/bin/env python3
"""Capture MS appendix GIF from live Oracle v5 (preset chip click, ~10s).

Requires: playwright (`pip install playwright` + `playwright install chromium`).
Output: reports/ms_rq019_paste_ready/ms_rq019_oracle_v5_visual_path_10s.gif
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "ms_rq019_paste_ready" / "ms_rq019_oracle_v5_visual_path_10s.gif"
URL = "https://jemaai.cloud/public_showroom_logos_oracle_v5.html"
CHIP_SUBSTR = "테마"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default=URL)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--duration-s", type=float, default=10.0)
    ap.add_argument("--fps", type=int, default=12)
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed: pip install playwright && playwright install chromium", file=sys.stderr)
        return 2

    try:
        import imageio.v2 as imageio
    except ImportError:
        print("imageio not installed: pip install imageio", file=sys.stderr)
        return 2

    frames: list = []
    interval = 1.0 / max(args.fps, 1)
    n_frames = int(args.duration_s * args.fps)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": args.width, "height": args.height})
        page.goto(args.url, wait_until="networkidle", timeout=90_000)
        page.wait_for_selector("#askBtn", timeout=60_000)
        time.sleep(0.8)
        chip = page.locator("button.chip").filter(has_text=CHIP_SUBSTR).first
        if chip.count() == 0:
            chip = page.locator("button.chip").first
        chip.click()
        for _ in range(n_frames):
            png = page.screenshot(type="png", full_page=False)
            frames.append(imageio.imread(png))
            time.sleep(interval)
        browser.close()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(str(args.out), frames, duration=interval, loop=0)
    print(f"Wrote {args.out} ({len(frames)} frames @ {args.fps}fps)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
