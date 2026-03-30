#!/usr/bin/env python3
"""Attach vector_4d to symbol candidate rows via gematria bridge."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.gematria_engine import build_gematria_metadata
from scripts.core.gematria_to_4d_bridge import build_gematria_4d_bridge

IN_JSONL = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_candidates_latest.jsonl"
OUT_JSONL = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_candidates_with_vector4d_latest.jsonl"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            obj = json.loads(s)
            if isinstance(obj, dict):
                yield obj


def main() -> int:
    ap = argparse.ArgumentParser(description="Join symbol rows with vector_4d")
    ap.add_argument("--input", default=str(IN_JSONL))
    ap.add_argument("--out", default=str(OUT_JSONL))
    args = ap.parse_args()

    in_path = _abs(args.input)
    out_path = _abs(args.out)
    if not in_path.is_file():
        print(f"ERROR: missing input: {in_path}")
        return 2

    rows: list[dict[str, Any]] = []
    for row in _iter_jsonl(in_path):
        symbol = str(row.get("symbol", "")).strip()
        if symbol:
            gem = build_gematria_metadata(raw_text=symbol, compressed_text=symbol, reconstructed_text=symbol)
            bridge = build_gematria_4d_bridge(gematria_metadata=gem)
            vec = bridge.get("vector_4d")
            if isinstance(vec, dict):
                row["vector_4d"] = {k: float(vec.get(k, 0.25)) for k in ("S", "L", "K", "M")}
                row["state16"] = bridge.get("state16")
                row["distance_to_state16"] = bridge.get("distance_to_state16")
        rows.append(row)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print("OK: symbol vector_4d join generated")
    print(f"out={out_path}")
    print(f"rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
