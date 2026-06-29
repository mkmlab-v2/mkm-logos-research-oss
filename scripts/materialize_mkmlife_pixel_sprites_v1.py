#!/usr/bin/env python3
"""Materialize mkmlife first-party pixel sprites under public/pixel_battalion/refined.

Deterministic 32x32 placeholders from character_map palette hints when CDN assets
are missing. Idempotent — skips existing files unless --force.

B-track UI asset lane; not Track A compression evidence.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PIXEL_JSON = ROOT / "projects/mkm/mkm-life/public/data/MKM_PIXEL_LANGUAGE_V1.json"
DEFAULT_CHAR_MAP = ROOT / "docs/final/artifacts/pixel_battalion_character_map_public_latest.json"
DEFAULT_OUT_DIR = ROOT / "projects/mkm/mkm-life/public/pixel_battalion/refined"
DEFAULT_REPORT = ROOT / "reports/mkmlife_pixel_sprites_materialize_v1_latest.json"

# filename -> (primary, shadow, highlight) RGB
_PALETTE_BY_FILENAME: dict[str, tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]] = {
    "generated_image_1774951706373_1.png": ((0, 190, 210), (20, 40, 80), (200, 210, 220)),
    "generated_image_1774954662935_1.png": ((230, 170, 50), (40, 38, 34), (250, 245, 235)),
    "generated_image_1774954940598_1.png": ((120, 60, 200), (20, 20, 28), (230, 200, 80)),
    "generated_image_1774955152838_1.png": ((200, 45, 55), (55, 65, 75), (175, 185, 195)),
    "generated_image_1774955172444_1.png": ((110, 210, 55), (45, 50, 55), (245, 245, 245)),
    "generated_image_1774955571752_1.png": ((95, 220, 175), (40, 80, 200), (250, 250, 250)),
    "generated_image_1774955748157_1.png": ((35, 120, 70), (18, 22, 24), (190, 160, 70)),
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _filename_from_url(url: str) -> str | None:
    m = re.search(r"([^/]+\.png)$", url.strip(), re.I)
    return m.group(1) if m else None


def collect_sprite_filenames(doc: dict[str, Any]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for reg_key in ("category_sprite_registry", "morning_beans_lane_registry"):
        reg = doc.get(reg_key) or {}
        if not isinstance(reg, dict):
            continue
        for entry in reg.values():
            if not isinstance(entry, dict):
                continue
            url = entry.get("sprite_url")
            if not isinstance(url, str):
                continue
            fn = _filename_from_url(url)
            if fn and fn not in seen:
                seen.add(fn)
                names.append(fn)
    return sorted(names)


def _draw_sprite(primary: tuple[int, int, int], shadow: tuple[int, int, int], highlight: tuple[int, int, int]):
    from PIL import Image

    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    px = img.load()
    assert px is not None
    for y in range(32):
        for x in range(32):
            if x < 2 or y < 2 or x > 29 or y > 29:
                px[x, y] = (*shadow, 255)
            elif 8 <= x <= 23 and 10 <= y <= 25:
                px[x, y] = (*primary, 255)
            elif (x + y) % 7 == 0 and 6 <= x <= 25 and 8 <= y <= 27:
                px[x, y] = (*highlight, 255)
    # simple "face" pixels
    for x, y in ((12, 14), (19, 14), (15, 20), (16, 20)):
        px[x, y] = (*shadow, 255)
    return img


def materialize(
    filenames: list[str],
    out_dir: Path,
    *,
    force: bool,
) -> list[dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for fn in filenames:
        dest = out_dir / fn
        if dest.is_file() and not force:
            rows.append({"filename": fn, "path": _rel(dest), "action": "skipped_exists"})
            continue
        palette = _PALETTE_BY_FILENAME.get(fn)
        if not palette:
            raise ValueError(f"no palette for {fn}")
        img = _draw_sprite(*palette)
        img.save(dest, format="PNG", optimize=True)
        rows.append({"filename": fn, "path": _rel(dest), "action": "written", "bytes": dest.stat().st_size})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pixel-json", type=Path, default=DEFAULT_PIXEL_JSON)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    pixel_path = args.pixel_json.resolve()
    if not pixel_path.is_file():
        print(f"error: missing pixel json: {pixel_path}", file=sys.stderr)
        return 2
    doc = json.loads(pixel_path.read_text(encoding="utf-8"))
    filenames = collect_sprite_filenames(doc)
    if not filenames:
        print("error: no sprite filenames in MKM_PIXEL_LANGUAGE", file=sys.stderr)
        return 2

    try:
        rows = materialize(filenames, args.out_dir.resolve(), force=args.force)
    except Exception as exc:
        print(f"error: materialize failed: {exc}", file=sys.stderr)
        return 1

    report = {
        "schema": "mkmlife_pixel_sprites_materialize_v1",
        "generated_at_utc": _utc(),
        "pixel_json": _rel(pixel_path),
        "out_dir": _rel(args.out_dir.resolve()),
        "file_count": len(rows),
        "written_count": sum(1 for r in rows if r.get("action") == "written"),
        "files": rows,
        "hypothesis_tag": "[HYPO]",
        "note": "First-party mkmlife sprites; replace with CDN originals when assets.jemaai.cloud restored.",
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "file_count": len(rows), "written": report["written_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
