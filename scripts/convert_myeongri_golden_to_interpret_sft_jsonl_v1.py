#!/usr/bin/env python3
"""Golden JSONL -> interpret-only SFT (engine JSON in prompt, envelope v1 as target).

Harness v2 curriculum: LLM must not recompute pillars; supervision cites engine saju.

Example::

  py scripts/convert_myeongri_golden_to_interpret_sft_jsonl_v1.py \\
    --input-jsonl data/training/myeongri_deterministic_lora_golden_bulk_v1/train.jsonl \\
    --output-jsonl data/training/myeongri_interpret_sft_v1/train.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.myeongri_deterministic_lora_golden_views_v1 import compact_expected_result  # noqa: E402
from scripts.myeongri_interpret_envelope_views_v1 import (  # noqa: E402
    sha256_canonical,
    template_envelope_from_compact,
)
from scripts.run_myeongri_ai_interpretation_pack_v1 import build_user_message  # noqa: E402

DEFAULT_ARTIFACT_PATHS = [
    "scripts/run_saju_global_birth_v1.py",
    "scripts/prep_myeongri_deterministic_lora_golden_v1.py",
]


def row_to_interpret_sft(row: dict, *, lang: str) -> dict[str, str]:
    exp = row.get("expected_result")
    if not isinstance(exp, dict):
        raise ValueError("expected_result must be an object")
    compact = compact_expected_result(exp)
    sha = sha256_canonical(compact)
    instruction = build_user_message(
        sha256_or_empty=sha,
        artifact_paths=list(DEFAULT_ARTIFACT_PATHS),
        deterministic_json_text=json.dumps(compact, ensure_ascii=False, indent=2),
        optional_timeline_md="",
        lang=lang,
    )
    envelope = template_envelope_from_compact(compact, lang=lang, deterministic_input_sha256=sha)
    output = json.dumps(envelope, ensure_ascii=False, separators=(",", ":"))
    return {"instruction": instruction, "output": output}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, required=True)
    ap.add_argument("--output-jsonl", type=Path, required=True)
    ap.add_argument("--lang", default="ko", choices=("ko", "en"))
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
            fout.write(json.dumps(row_to_interpret_sft(row, lang=args.lang), ensure_ascii=False) + "\n")
            n += 1

    print(json.dumps({"ok": True, "rows": n, "out": str(args.output_jsonl)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
