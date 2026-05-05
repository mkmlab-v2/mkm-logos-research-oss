#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.7, K:0.8, M:0.4}
# Balance: 88
# Purpose: Bootstrap quaternion history for dynamic fragility thresholds.
# Keywords: fragility, quaternion, bootstrap, history, thresholds

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "macro_fragility_inputs_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return doc if isinstance(doc, dict) else {}


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Bootstrap quaternion history in macro fragility input payload.")
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--min-count", type=int, default=14)
    p.add_argument("--seed", default="0.12,0.16,0.20,0.24,0.27,0.31,0.35,0.29,0.33,0.37,0.41,0.46,0.39,0.34")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    in_path = args.input if args.input.is_absolute() else (ROOT / args.input)
    doc = _read_json(in_path)
    if not doc:
        print(f"bootstrap_fragility_quaternion_history_v1: SKIP (missing input) -> {in_path}")
        return 0

    hist = doc.get("quaternion_history")
    if not isinstance(hist, list):
        hist = []
    hist_values = [_to_float(x, -1.0) for x in hist]
    hist_values = [x for x in hist_values if x >= 0.0]

    if len(hist_values) >= max(1, args.min_count):
        print(f"bootstrap_fragility_quaternion_history_v1: SKIP (already {len(hist_values)} entries)")
        return 0

    seed_vals = []
    for token in str(args.seed).split(","):
        token = token.strip()
        if not token:
            continue
        seed_vals.append(_to_float(token, 0.0))
    if not seed_vals:
        seed_vals = [0.12, 0.16, 0.20, 0.24, 0.27, 0.31, 0.35, 0.29, 0.33, 0.37, 0.41, 0.46, 0.39, 0.34]

    merged = (hist_values + seed_vals)[-60:]
    doc["quaternion_history"] = merged
    _write_json(in_path, doc)
    print(f"bootstrap_fragility_quaternion_history_v1: PASS -> {in_path} (count={len(merged)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
