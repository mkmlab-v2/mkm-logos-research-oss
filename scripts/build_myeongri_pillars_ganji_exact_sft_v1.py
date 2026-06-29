#!/usr/bin/env python3
"""Pillars-only SFT with explicit Korean ganji format contract (no Gan/Ji placeholders)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from myeongri_deterministic_lora_golden_views_v1 import (
    instruction_pillars_only_from_golden_row,
    pillars_only_supervision_v1,
)

_GANJI_CONTRACT = (
    "GANJI_FORMAT_LOCK: saju.year/month/day/hour MUST be two-character Korean ganji "
    "labels from standard manseoryeok (examples: 병신, 정유, 갑자, 임오). "
    "FORBIDDEN: English words (Gan, Ji, Xu, Ren), pinyin, romanization, single Latin letters, "
    "or placeholder tokens. Copy the exact ganji strings shown in the training target."
)


def _row_to_sft(row: dict[str, Any]) -> dict[str, str]:
    exp = row.get("expected_result")
    if not isinstance(exp, dict):
        raise ValueError("expected_result must be an object")
    target = pillars_only_supervision_v1(exp)
    saju = target.get("saju") if isinstance(target.get("saju"), dict) else {}
    example = (
        f"REFERENCE_GANJI_EXAMPLE (format only; compute for THIS birth): "
        f"year={saju.get('year')!r}, month={saju.get('month')!r}, "
        f"day={saju.get('day')!r}, hour={saju.get('hour')!r}."
    )
    instruction = instruction_pillars_only_from_golden_row(row, birth_emphasis=True)
    instruction = f"{instruction}\n{_GANJI_CONTRACT}\n{example}"
    out = json.dumps(target, ensure_ascii=False, separators=(",", ":"))
    return {"instruction": instruction, "output": out}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, required=True)
    ap.add_argument("--output-jsonl", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=0, help="Max golden rows (0=all)")
    args = ap.parse_args()
    if not args.input_jsonl.is_file():
        raise SystemExit(f"missing input: {args.input_jsonl}")

    n = 0
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.input_jsonl.open("r", encoding="utf-8-sig") as fin, args.output_jsonl.open(
        "w", encoding="utf-8"
    ) as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            if args.limit > 0 and n >= args.limit:
                break
            row = json.loads(line)
            fout.write(json.dumps(_row_to_sft(row), ensure_ascii=False) + "\n")
            n += 1

    print(
        json.dumps(
            {
                "ok": True,
                "rows": n,
                "out": str(args.output_jsonl),
                "curriculum": "pillars_ganji_exact_v1",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
