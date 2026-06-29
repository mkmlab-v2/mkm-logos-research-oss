#!/usr/bin/env python3
"""Build HAAN lens coordinate maps for logos · myeongri · ijeoma (B-track)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_lens_corpus_coordinate_map_v1 import LENS_OUT, build_coordinate_map

DEFAULT_OUT = ROOT / "docs/final/artifacts/haan_lens_coordinate_maps_v1_latest.json"
LANES = ("logos", "myeongri", "ijeoma")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    maps: dict[str, dict] = {}
    for lens in LANES:
        doc = build_coordinate_map(lens=lens)
        out = LENS_OUT[lens]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        maps[lens] = {
            "map_path": out.relative_to(ROOT).as_posix(),
            "paper_count": doc["paper_count"],
            "field_totals": doc.get("field_totals") or {},
            "cluster_keys": sorted((doc.get("clusters") or {}).keys()),
        }

    bundle = {
        "schema": "haan_lens_coordinate_maps_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "research_only": True,
        "lanes": maps,
        "reproduce": "py scripts/build_haan_lens_coordinate_maps_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out), "lanes": {k: v["paper_count"] for k, v in maps.items()}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
