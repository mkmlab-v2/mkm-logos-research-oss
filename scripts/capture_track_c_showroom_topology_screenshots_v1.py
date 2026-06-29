#!/usr/bin/env python3
"""Capture Track C B2B deck showroom screenshots (topology + meaning graph + oracle v6)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "reports/track_c_showroom_deck_screenshots_v1"
DEFAULT_MANIFEST = ROOT / "reports/track_c_showroom_deck_screenshots_manifest_v1_latest.json"

TARGETS: tuple[tuple[str, str], ...] = (
    ("topology_radar", "https://jemaai.cloud/legacy/public_showroom_topology_radar_v1.html"),
    ("meaning_topology_graph", "https://jemaai.cloud/legacy/public_showroom_meaning_topology_graph_v1.html"),
    ("logos_oracle_v6", "https://jemaai.cloud/legacy/public_showroom_logos_oracle_v6.html?product=1"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--viewport-width", type=int, default=1440)
    ap.add_argument("--viewport-height", type=int, default=900)
    ap.add_argument("--wait-ms", type=int, default=2500)
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(f"playwright not installed: {exc}") from exc

    args.out_dir.mkdir(parents=True, exist_ok=True)
    captured: list[dict[str, Any]] = []
    errors: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": args.viewport_width, "height": args.viewport_height})
        for slug, url in TARGETS:
            out_png = args.out_dir / f"{slug}_v1.png"
            try:
                resp = page.goto(url, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(args.wait_ms)
                page.screenshot(path=str(out_png), full_page=False)
                captured.append(
                    {
                        "slug": slug,
                        "url": url,
                        "png": str(out_png.relative_to(ROOT)).replace("\\", "/"),
                        "http_status": resp.status if resp else None,
                        "ok": out_png.is_file() and out_png.stat().st_size > 0,
                    }
                )
            except Exception as exc:  # noqa: BLE001 — capture per-URL failures
                errors.append(f"{slug}: {exc}")
                captured.append({"slug": slug, "url": url, "ok": False, "error": str(exc)})
        browser.close()

    manifest = {
        "schema": "track_c_showroom_deck_screenshots_manifest_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "gating_status": "NON_GATING",
        "out_dir": str(args.out_dir.relative_to(ROOT)).replace("\\", "/"),
        "captured": captured,
        "ok": all(row.get("ok") for row in captured) and not errors,
        "errors": errors,
        "deck_usage_note": "Internal B2B deck only; no win-rate or path-leak captions.",
    }
    args.manifest_json.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": manifest["ok"], "manifest": str(args.manifest_json), "count": len(captured)}, ensure_ascii=False))
    return 0 if manifest["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
