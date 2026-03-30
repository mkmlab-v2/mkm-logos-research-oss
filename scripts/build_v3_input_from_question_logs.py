#!/usr/bin/env python3
"""Build V3 input dataset by auto-sampling from question log JSONL."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IN = ROOT / "reports" / "constitution" / "operation_question_log_latest.jsonl"
DEFAULT_OUT = ROOT / "reports" / "constitution" / "v3" / "v3_input_dataset_latest.jsonl"
DEFAULT_SUMMARY = ROOT / "reports" / "constitution" / "v3" / "v3_sampling_summary_latest.json"


def _abs_path(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (ROOT / p)


def _pick_text(row: dict[str, Any], keys: list[str]) -> str:
    for k in keys:
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                continue
            prompt = _pick_text(raw, ["question", "prompt", "query", "user_input"])
            response = _pick_text(raw, ["answer", "response", "assistant_output", "output"])
            if not prompt or not response:
                continue
            rows.append(raw)
    return rows


def _split_bounds(total: int, train_ratio: float, val_ratio: float) -> tuple[int, int]:
    if total <= 0:
        return (0, 0)
    train_count = int(total * train_ratio)
    val_count = int(total * val_ratio)
    if total >= 3:
        if train_count <= 0:
            train_count = 1
        if val_count <= 0:
            val_count = 1
        if train_count + val_count >= total:
            val_count = max(1, total - train_count - 1)
            train_count = max(1, total - val_count - 1)
    else:
        # For very tiny samples, keep deterministic ordering without forcing all buckets.
        if train_count <= 0:
            train_count = 1
        val_count = 0
    return (train_count, train_count + val_count)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build V3 input set from question log JSONL")
    ap.add_argument("--in", dest="input_path", default=str(DEFAULT_IN), help="Question log JSONL")
    ap.add_argument("--out", dest="output_path", default=str(DEFAULT_OUT), help="V3 output JSONL")
    ap.add_argument("--summary-out", dest="summary_path", default=str(DEFAULT_SUMMARY), help="Sampling summary JSON")
    ap.add_argument("--sample-size", type=int, default=200, help="Sample count (<=0 means all)")
    ap.add_argument("--seed", type=int, default=42, help="Random seed")
    ap.add_argument("--train-ratio", type=float, default=0.8, help="Train split ratio")
    ap.add_argument("--val-ratio", type=float, default=0.1, help="Validation split ratio")
    args = ap.parse_args()

    in_path = _abs_path(args.input_path)
    out_path = _abs_path(args.output_path)
    summary_path = _abs_path(args.summary_path)

    if not in_path.is_file():
        print(f"❌ input not found: {in_path}")
        return 1
    if args.sample_size < 0:
        print("❌ --sample-size must be >= 0")
        return 1
    if not (0.0 < args.train_ratio < 1.0) or not (0.0 <= args.val_ratio < 1.0):
        print("❌ invalid split ratios")
        return 1
    if args.train_ratio + args.val_ratio >= 1.0:
        print("❌ train_ratio + val_ratio must be < 1.0")
        return 1

    source_rows = _load_rows(in_path)
    if not source_rows:
        print("❌ no valid rows with question/answer pairs")
        return 1

    rng = random.Random(args.seed)
    sample_size = len(source_rows) if args.sample_size == 0 else min(args.sample_size, len(source_rows))
    sampled = rng.sample(source_rows, sample_size)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    train_end, val_end = _split_bounds(sample_size, args.train_ratio, args.val_ratio)
    split_counts = {"train": 0, "val": 0, "test": 0}
    with out_path.open("w", encoding="utf-8") as f:
        for i, raw in enumerate(sampled):
            prompt = _pick_text(raw, ["question", "prompt", "query", "user_input"])
            response = _pick_text(raw, ["answer", "response", "assistant_output", "output"])
            split = "train" if i < train_end else ("val" if i < val_end else "test")
            split_counts[split] += 1
            row = {
                "v3_id": f"v3_{i+1:06d}",
                "source_log_id": str(raw.get("id", raw.get("log_id", f"row_{i+1}"))),
                "prompt": prompt,
                "response": response,
                "split": split,
                "quality_gate_passed": True,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "schema": "v3_sampling_summary_v1",
        "source_input": str(in_path),
        "output_dataset": str(out_path),
        "requested_sample_size": args.sample_size,
        "sampled_size": sample_size,
        "seed": args.seed,
        "split_ratio": {"train": args.train_ratio, "val": args.val_ratio, "test": 1.0 - args.train_ratio - args.val_ratio},
        "split_counts": split_counts,
    }
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("✅ V3 input dataset built")
    print(f"dataset: {out_path.resolve()}")
    print(f"summary: {summary_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
