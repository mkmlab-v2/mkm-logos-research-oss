#!/usr/bin/env python3
"""Generate performance report from V3 input dataset JSONL."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IN = ROOT / "reports" / "constitution" / "v3" / "v3_input_dataset_latest.jsonl"
DEFAULT_OUT = ROOT / "reports" / "constitution" / "v3" / "v3_performance_report_latest.json"


def _abs_path(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (ROOT / p)


def _pair_hash(prompt: str, response: str) -> str:
    return hashlib.sha256(f"{prompt}\n<SEP>\n{response}".encode("utf-8")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Report V3 measured pipeline performance")
    ap.add_argument("--in", dest="input_path", default=str(DEFAULT_IN), help="V3 dataset JSONL")
    ap.add_argument("--out", dest="output_path", default=str(DEFAULT_OUT), help="Performance report JSON")
    args = ap.parse_args()

    in_path = _abs_path(args.input_path)
    out_path = _abs_path(args.output_path)

    if not in_path.is_file():
        print(f"❌ input not found: {in_path}")
        return 1

    total = 0
    split_counter: Counter[str] = Counter()
    duplicate_pairs = 0
    prompt_len_sum = 0
    response_len_sum = 0
    seen: set[str] = set()

    with in_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            prompt = str(row.get("prompt", "")).strip()
            response = str(row.get("response", "")).strip()
            split = str(row.get("split", "unknown"))
            total += 1
            split_counter[split] += 1
            prompt_len_sum += len(prompt)
            response_len_sum += len(response)
            h = _pair_hash(prompt, response)
            if h in seen:
                duplicate_pairs += 1
            else:
                seen.add(h)

    if total == 0:
        print("❌ empty dataset")
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "v3_pipeline_performance_report_v1",
        "source_input": str(in_path),
        "dataset_metrics": {
            "total_records": total,
            "split_distribution": dict(split_counter),
            "duplicate_prompt_response_pairs": duplicate_pairs,
            "unique_prompt_response_pairs": len(seen),
            "avg_prompt_length": round(prompt_len_sum / total, 2),
            "avg_response_length": round(response_len_sum / total, 2),
        },
        "quality_gate": {
            "pass": duplicate_pairs == 0 and total > 0,
            "rules": {
                "no_duplicates": duplicate_pairs == 0,
                "non_empty_dataset": total > 0,
            },
        },
    }
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("✅ V3 performance report generated")
    print(f"report: {out_path.resolve()}")
    return 0 if report["quality_gate"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
