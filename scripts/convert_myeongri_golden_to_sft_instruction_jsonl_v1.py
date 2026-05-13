#!/usr/bin/env python3
"""Convert Pack 0-B golden JSONL (myeongri_deterministic_lora_golden_set_v1) to SFT instruction/output JSONL.

``train_mkm_prophecy_lora_windows_fallback_v1.py`` / Unsloth trainers expect each line::

  {"instruction": "...", "output": "..."}

The output string is the compact JSON of ``expected_result`` (deterministic saju body).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _row_to_sft(row: dict) -> dict[str, str]:
    utc = str(row.get("birth_instant_utc") or "").strip()
    tz = str(row.get("iana_tz") or "").strip()
    male = row.get("is_male")
    if male is None:
        male_s = "unspecified (engine default false)"
    else:
        male_s = "true" if male else "false"
    exp = row.get("expected_result")
    if not isinstance(exp, dict):
        raise ValueError("expected_result must be an object")
    instruction = (
        "Deterministic myeongri task. Given birth_instant_utc, iana_tz, is_male — "
        "emit ONLY valid JSON for schema saju_global_birth_result_v1 "
        "(fields: schema, version, resolution, full_saju; omit calculated_at under full_saju).\n"
        f"birth_instant_utc: {utc}\n"
        f"iana_tz: {tz}\n"
        f"is_male: {male_s}"
    )
    out = json.dumps(exp, ensure_ascii=False, separators=(",", ":"))
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
            sft = _row_to_sft(row)
            fout.write(json.dumps(sft, ensure_ascii=False) + "\n")
            n += 1
    print(json.dumps({"ok": True, "rows": n, "out": str(args.output_jsonl)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
