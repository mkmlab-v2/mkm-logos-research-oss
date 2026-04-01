# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.6, L:0.5, K:0.5, M:0.7}
# Balance: 75
# Purpose: Build public CDN character map from pilot map (PIXEL_BATTALION_BASE_URL).
"""Transform pilot pixel map file URLs into public CDN URLs."""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "docs" / "final" / "artifacts" / "pixel_battalion_character_map_pilot.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "pixel_battalion_character_map_public_latest.json"


def _default_base() -> str:
    return os.getenv("PIXEL_BATTALION_BASE_URL", "https://assets.jemaai.cloud/pixel_battalion/refined").strip().rstrip(
        "/"
    )


def main() -> None:
    if not PILOT.exists():
        raise SystemExit(f"pilot map missing: {PILOT}")
    base = _default_base()
    doc = json.loads(PILOT.read_text(encoding="utf-8"))
    chars = doc.get("pilot_characters") or []
    for row in chars:
        if not isinstance(row, dict):
            continue
        fn = row.get("image_filename") or ""
        if fn:
            row["image_url"] = f"{base}/{fn}"
    doc["public_base_url"] = base
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} (base={base}, characters={len(chars)})")


if __name__ == "__main__":
    main()
