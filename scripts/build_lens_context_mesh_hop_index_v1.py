#!/usr/bin/env python3
"""Build lens context mesh hop index from graph slice JSON."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lens_context_mesh_v1 import (  # noqa: E402
    DEFAULT_LOGOS_SLICE,
    build_hop_index_from_slice,
    load_json,
)

DEFAULT_OUT = ROOT / "docs/final/artifacts/lens_context_mesh_hop_index_logos_v1_latest.json"
DEFAULT_STUDIO_MIRROR = ROOT / "projects/no1kmedi/public/data/logos_studio/context_mesh_hop_index_v1.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="Build lens_context_mesh_hop_index_v1 from graph slice")
    ap.add_argument("--slice-json", type=Path, default=DEFAULT_LOGOS_SLICE)
    ap.add_argument("--lens-id", default="logos")
    ap.add_argument("--pack-id", default="lens_pack@logos_showroom")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--studio-mirror", type=Path, default=DEFAULT_STUDIO_MIRROR)
    ap.add_argument("--no-studio-mirror", action="store_true")
    args = ap.parse_args()

    if not args.slice_json.is_file():
        print(json.dumps({"ok": False, "error": f"slice missing: {args.slice_json}"}))
        return 2

    slice_doc = load_json(args.slice_json)
    rel_src = str(args.slice_json.relative_to(ROOT)).replace("\\", "/")
    doc = build_hop_index_from_slice(
        slice_doc,
        lens_id=args.lens_id,
        pack_id=args.pack_id,
        source_slice_path=rel_src,
    )

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.write_text(text, encoding="utf-8")

    if not args.no_studio_mirror:
        args.studio_mirror.parent.mkdir(parents=True, exist_ok=True)
        args.studio_mirror.write_text(text, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out_json),
                "studio_mirror": None if args.no_studio_mirror else str(args.studio_mirror),
                "node_count": doc["stats"]["node_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
