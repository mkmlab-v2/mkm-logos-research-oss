#!/usr/bin/env python3
"""Build a focused hard-negative SFT JSONL for one sample_id."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample-id", required=True)
    ap.add_argument(
        "--golden-jsonl",
        type=Path,
        default=ROOT / "data/training/myeongri_deterministic_lora_golden_bulk_v1/train.jsonl",
    )
    ap.add_argument(
        "--out-jsonl",
        type=Path,
        default=ROOT / "data/training/myeongri_deterministic_lora_hard_negative_sft_focus_latest.jsonl",
    )
    args = ap.parse_args()

    if not args.golden_jsonl.is_file():
        raise SystemExit(f"missing golden: {args.golden_jsonl}")

    row = None
    with args.golden_jsonl.open("r", encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("sample_id") == args.sample_id:
                row = obj
                break

    if not isinstance(row, dict):
        raise SystemExit(f"sample_id not found: {args.sample_id}")
    exp = row.get("expected_result")
    if not isinstance(exp, dict):
        raise SystemExit("expected_result missing")

    male = row.get("is_male")
    male_s = "unspecified (engine default false)" if male is None else ("true" if male else "false")
    instruction = (
        "STRICT deterministic myeongri task.\n"
        "Return ONLY one valid JSON object for schema saju_global_birth_result_v1.\n"
        "No markdown, no explanation, no extra keys, no trailing text.\n"
        "Required top-level keys: schema, version, resolution, full_saju.\n"
        "If full_saju.calculated_at exists, omit it.\n"
        f"birth_instant_utc: {str(row.get('birth_instant_utc') or '').strip()}\n"
        f"iana_tz: {str(row.get('iana_tz') or '').strip()}\n"
        f"is_male: {male_s}"
    )
    rec = {
        "sample_id": args.sample_id,
        "split": row.get("split"),
        "hard_negative_reason": "json_parse_failed_focus",
        "instruction": instruction,
        "output": json.dumps(exp, ensure_ascii=False, separators=(",", ":")),
    }
    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.out_jsonl.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out_jsonl": str(args.out_jsonl), "sample_id": args.sample_id}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

