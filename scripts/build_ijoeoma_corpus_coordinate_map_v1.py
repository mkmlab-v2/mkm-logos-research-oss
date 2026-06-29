#!/usr/bin/env python3
"""Aggregate ijeoma lens coordinate hits — wrapper for build_lens_corpus_coordinate_map_v1."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_lens_corpus_coordinate_map_v1 import LENS_OUT, build_coordinate_map


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LENS_OUT["ijeoma"])
    args = ap.parse_args()
    doc = build_coordinate_map(lens="ijeoma")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "paper_count": doc["paper_count"], "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
