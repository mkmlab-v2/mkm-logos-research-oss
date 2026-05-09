#!/usr/bin/env python3
"""Split LoRA JSONL by split metadata into train/validation/test/locked_eval files."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IN = WORKSPACE_ROOT / "scripts" / "data" / "mkm_control_integrity_golden_set_v1_lora_1000.jsonl"
DEFAULT_OUT_DIR = WORKSPACE_ROOT / "scripts" / "data" / "mkm_control_integrity_lora_splits_v1"
SPLITS = ("train", "validation", "test", "locked_eval")


def _as_abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (WORKSPACE_ROOT / p)


def main() -> int:
    ap = argparse.ArgumentParser(description="Split LoRA JSONL by metadata.split")
    ap.add_argument("--in", dest="input_path", default=str(DEFAULT_IN), help="Input LoRA JSONL")
    ap.add_argument("--out-dir", dest="out_dir", default=str(DEFAULT_OUT_DIR), help="Output directory")
    args = ap.parse_args()

    input_path = _as_abs(args.input_path)
    out_dir = _as_abs(args.out_dir)
    if not input_path.is_file():
        print(f"input not found: {input_path}")
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    out_files = {sp: (out_dir / f"{sp}.jsonl").open("w", encoding="utf-8") for sp in SPLITS}
    counter: Counter[str] = Counter()
    unknown = 0
    total = 0

    try:
        with input_path.open("r", encoding="utf-8") as src:
            for line_no, raw in enumerate(src, start=1):
                line = raw.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    print(f"line {line_no}: invalid json: {exc}")
                    return 2
                split = str(row.get("metadata", {}).get("split", "unknown"))
                total += 1
                if split in out_files:
                    out_files[split].write(json.dumps(row, ensure_ascii=False) + "\n")
                    counter[split] += 1
                else:
                    unknown += 1
    finally:
        for f in out_files.values():
            f.close()

    print(f"rows={total}")
    print(f"unknown_split={unknown}")
    for sp in SPLITS:
        print(f"{sp}={counter.get(sp, 0)}")
    print(f"out_dir={out_dir}")
    return 0 if unknown == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
