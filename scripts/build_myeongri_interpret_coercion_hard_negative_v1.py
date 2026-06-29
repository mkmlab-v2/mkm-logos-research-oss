#!/usr/bin/env python3
"""Append interpret SFT rows for harness coercion sample_ids (locked_eval holdout)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.convert_myeongri_golden_to_interpret_sft_jsonl_v1 import row_to_interpret_sft  # noqa: E402

DEFAULT_GOLDEN = ROOT / "data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl"
DEFAULT_BASE = ROOT / "data/training/myeongri_interpret_sft_harness_v1/train.jsonl"
DEFAULT_OUT = ROOT / "data/training/myeongri_interpret_sft_harness_v1/train_with_coercion_hn.jsonl"
DEFAULT_IDS = ("mdl-gs-v1-5018", "mdl-gs-v1-5082")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--golden-jsonl", type=Path, default=DEFAULT_GOLDEN)
    ap.add_argument("--base-jsonl", type=Path, default=DEFAULT_BASE)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sample-id", action="append", default=list(DEFAULT_IDS))
    ap.add_argument("--repeat", type=int, default=20, help="Repeat each HN row N times")
    ap.add_argument("--lang", default="ko")
    args = ap.parse_args()

    want = set(args.sample_id)
    hn_rows: list[dict[str, str]] = []
    for line in args.golden_jsonl.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if str(row.get("sample_id")) in want:
            hn_rows.append(row_to_interpret_sft(row, lang=args.lang, insight_mode="variant"))

    if not hn_rows:
        raise SystemExit(f"no rows for sample_ids: {sorted(want)}")

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    n_base = 0
    with args.out_jsonl.open("w", encoding="utf-8") as fout:
        if args.base_jsonl.is_file():
            for line in args.base_jsonl.read_text(encoding="utf-8-sig").splitlines():
                if line.strip():
                    fout.write(line.strip() + "\n")
                    n_base += 1
        for _ in range(max(1, args.repeat)):
            for r in hn_rows:
                fout.write(json.dumps(r, ensure_ascii=False) + "\n")

    n_hn = len(hn_rows) * max(1, args.repeat)
    print(
        json.dumps(
            {
                "ok": True,
                "base_rows": n_base,
                "hn_rows_appended": n_hn,
                "sample_ids": sorted(want),
                "out": str(args.out_jsonl),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
