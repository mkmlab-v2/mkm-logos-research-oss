#!/usr/bin/env python3
"""Build lens_context_mesh_hub_v1 manifest for Logos showroom pack."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lens_context_mesh_v1 import (  # noqa: E402
    DEFAULT_LOGOS_LATTICE,
    DEFAULT_LOGOS_LATTICE_GENESIS,
    DEFAULT_LOGOS_SLICE,
    build_hub_logos,
)

DEFAULT_HOP = ROOT / "docs/final/artifacts/lens_context_mesh_hop_index_logos_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/lens_context_mesh_hub_logos_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="Build lens_context_mesh_hub_v1 (logos)")
    ap.add_argument("--slice-json", type=Path, default=DEFAULT_LOGOS_SLICE)
    ap.add_argument("--hop-index-json", type=Path, default=DEFAULT_HOP)
    ap.add_argument("--lattice-json", type=Path, default=DEFAULT_LOGOS_LATTICE)
    ap.add_argument("--lattice-genesis-json", type=Path, default=DEFAULT_LOGOS_LATTICE_GENESIS)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.hop_index_json.is_file():
        print(json.dumps({"ok": False, "error": f"hop index missing: {args.hop_index_json}"}))
        return 2

    doc = build_hub_logos(
        slice_path=args.slice_json,
        hop_index_path=args.hop_index_json,
        lattice_path=args.lattice_json,
        lattice_genesis_path=args.lattice_genesis_json,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
