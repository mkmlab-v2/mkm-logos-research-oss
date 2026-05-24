#!/usr/bin/env python3
"""Build Pack 0-B tier-0 SFT JSONL: instruction + four-pillar ganji supervision only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from myeongri_deterministic_lora_golden_views_v1 import (
    instruction_pillars_only_from_golden_row,
    pillars_only_supervision_v1,
)


def _row_to_sft(row: dict) -> dict[str, str]:
    exp = row.get("expected_result")
    if not isinstance(exp, dict):
        raise ValueError("expected_result must be an object")
    target = pillars_only_supervision_v1(exp)
    instruction = instruction_pillars_only_from_golden_row(row)
    out = json.dumps(target, ensure_ascii=False, separators=(",", ":"))
    return {"instruction": instruction, "output": out}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, required=True)
    ap.add_argument("--output-jsonl", type=Path, required=True)
    args = ap.parse_args()
    if not args.input_jsonl.is_file():
        raise SystemExit(f"missing input: {args.input_jsonl}")

    n = 0
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.input_jsonl.open("r", encoding="utf-8-sig") as fin, args.output_jsonl.open(
        "w", encoding="utf-8"
    ) as fout:
        for i, line in enumerate(fin, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("schema_version") != "myeongri_deterministic_lora_golden_set_v1":
                print(f"warn line {i}: unexpected schema_version", file=sys.stderr)
            fout.write(json.dumps(_row_to_sft(row), ensure_ascii=False) + "\n")
            n += 1

    print(
        json.dumps(
            {
                "ok": True,
                "rows": n,
                "out": str(args.output_jsonl),
                "curriculum": "pillars_only_v1",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
