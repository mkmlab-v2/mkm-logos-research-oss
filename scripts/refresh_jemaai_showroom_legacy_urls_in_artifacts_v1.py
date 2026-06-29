#!/usr/bin/env python3
"""Refresh stale jemaai.cloud root showroom URLs -> /legacy/ or observe canonical."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/final/artifacts/jemaai_showroom_legacy_url_refresh_v1_latest.json"

# Order matters: more specific first
REPLACEMENTS: list[tuple[str, str]] = [
    (
        "https://api.jemaai.cloud/public_showroom_board_minimal.html",
        "https://jemaai.cloud/public_observe_v1.html",
    ),
    (
        "https://jemaai.cloud/public_showroom_board_minimal.html",
        "https://jemaai.cloud/public_observe_v1.html",
    ),
    (
        "https://jemaai.cloud/public_showroom_",
        "https://jemaai.cloud/legacy/public_showroom_",
    ),
]

SKIP_GLOBS = {
    "UNIVERSAL_COMPRESSION_BENCH_MATRIX_INPUT_V1.json",
    "finance_macro_b2b_compression_eval_input_v1.json",
    "universal_compression_bench_lane_enterprise_general_v1.json",
}

EXTRA_FILES = [
    ROOT / "docs/final/artifacts/regime_lens_style_focus_locked_v1.json",
    ROOT / "docs/final/artifacts/personadiary_daily_response_package_body_rhythm_sample_v1.json",
]

TARGET_DIRS = [
    ROOT / "docs/final/artifacts",
    ROOT / "reports",
    ROOT / "projects/mkm/mkm-life/public/data",
    ROOT / "projects/mkm/mkm-life/data/internal",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _apply(text: str) -> tuple[str, int]:
    total = 0
    for old, new in REPLACEMENTS:
        count = text.count(old)
        if count:
            text = text.replace(old, new)
            total += count
    # Fix double legacy prefix if re-run
    double = "https://jemaai.cloud/legacy/legacy/public_showroom_"
    while double in text:
        text = text.replace(double, "https://jemaai.cloud/legacy/public_showroom_")
    return text, total


def _iter_files() -> list[Path]:
    out: list[Path] = []
    for base in TARGET_DIRS:
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.name in SKIP_GLOBS:
                continue
            if path.suffix.lower() not in {".json", ".md", ".txt"}:
                continue
            if "_latest" not in path.name and path.parent.name != "data":
                # artifacts/reports: *_latest only; mkmlife data: all json
                if "mkm-life" not in path.as_posix():
                    continue
            out.append(path)
    return sorted(set(out + [p for p in EXTRA_FILES if p.is_file()]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    changed: list[dict[str, Any]] = []
    total_replacements = 0

    for path in _iter_files():
        raw = path.read_text(encoding="utf-8")
        new_text, n = _apply(raw)
        if n == 0:
            continue
        total_replacements += n
        rel = path.relative_to(ROOT).as_posix()
        changed.append({"path": rel, "replacements": n})
        if not args.dry_run:
            path.write_text(new_text, encoding="utf-8")

    doc = {
        "schema": "jemaai_showroom_legacy_url_refresh_v1",
        "generated_at_utc": _utc_now(),
        "dry_run": args.dry_run,
        "files_changed": len(changed),
        "total_replacements": total_replacements,
        "changed": changed,
        "repro": "py scripts/refresh_jemaai_showroom_legacy_urls_in_artifacts_v1.py",
    }
    if not args.dry_run:
        MANIFEST.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, **doc}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
