#!/usr/bin/env python3
"""Tune confidence calibration for Sasang prediction JSONL.

Track B / synthetic preparation utility:
- Rewrites confidence with a bounded affine transform.
- Keeps class prediction unchanged.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _safe_float(v: Any) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return None
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, required=True)
    ap.add_argument("--output-jsonl", type=Path, required=True)
    ap.add_argument("--scale", type=float, default=0.20)
    ap.add_argument("--offset", type=float, default=0.80)
    ap.add_argument("--max-confidence", type=float, default=0.99)
    args = ap.parse_args()

    if not args.input_jsonl.is_file():
        print(f"ERROR: missing input: {args.input_jsonl}")
        return 2

    lines_out: list[str] = []
    rewritten = 0
    kept = 0
    for line in args.input_jsonl.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            continue
        c = _safe_float(row.get("confidence"))
        if c is None:
            kept += 1
            lines_out.append(json.dumps(row, ensure_ascii=False))
            continue
        c_new = _clamp01((c * float(args.scale)) + float(args.offset))
        c_new = min(c_new, float(args.max_confidence))
        row["confidence"] = round(c_new, 6)
        row["calibration_tag"] = "sasang_confidence_affine_v1"
        rewritten += 1
        lines_out.append(json.dumps(row, ensure_ascii=False))

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.output_jsonl.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
    print(f"OK: wrote {args.output_jsonl}")
    print(f"rewritten={rewritten}, kept={kept}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
