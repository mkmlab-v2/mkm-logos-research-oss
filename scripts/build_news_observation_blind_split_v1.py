#!/usr/bin/env python3
"""Assign blind dataset partitions for news_observation_v1 JSONL.

Deterministic split by observation_id hash; independent from labels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs" / "final" / "artifacts" / "news_observation_v1_latest.jsonl"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "news_observation_v1_blind_split_latest.jsonl"


def _bucket(observation_id: str) -> int:
    h = hashlib.sha256(observation_id.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % 100


def _partition(obs_id: str, train_pct: int, calib_pct: int) -> str:
    b = _bucket(obs_id)
    if b < train_pct:
        return "train_holdout"
    if b < train_pct + calib_pct:
        return "calibration"
    return "locked_eval"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--train-pct", type=int, default=70)
    ap.add_argument("--calibration-pct", type=int, default=15)
    args = ap.parse_args()

    if not args.input_jsonl.is_file():
        raise SystemExit(f"Missing input JSONL: {args.input_jsonl}")
    if args.train_pct < 0 or args.calibration_pct < 0 or args.train_pct + args.calibration_pct > 100:
        raise SystemExit("Invalid split percentages.")

    out_lines: list[str] = []
    counts = {"train_holdout": 0, "calibration": 0, "locked_eval": 0}
    for ln in args.input_jsonl.read_text(encoding="utf-8-sig").splitlines():
        if not ln.strip():
            continue
        row = json.loads(ln)
        if not isinstance(row, dict) or row.get("schema_version") != "news_observation_v1":
            continue
        obs_id = str(row.get("observation_id") or "")
        if not obs_id:
            continue
        part = _partition(obs_id, args.train_pct, args.calibration_pct)
        row["dataset_partition"] = part
        counts[part] += 1
        out_lines.append(json.dumps(row, ensure_ascii=False))

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.output_jsonl.write_text("\n".join(out_lines) + ("\n" if out_lines else ""), encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "out": str(args.output_jsonl), "rows": len(out_lines), "split_counts": counts},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

