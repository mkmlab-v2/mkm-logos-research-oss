#!/usr/bin/env python3
"""[HYPO] Build long-form spine bench slice from universal matrix (min utf-8 bytes filter)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MATRIX = ROOT / "docs/final/artifacts/UNIVERSAL_COMPRESSION_BENCH_MATRIX_INPUT_V1.json"
OUT_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/NEXTGEN_LONGFORM_SPINE_BENCH_INPUT_V1.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--matrix-input", type=Path, default=MATRIX)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--min-raw-bytes", type=int, default=512)
    ap.add_argument("--max-cases", type=int, default=200)
    ap.add_argument(
        "--domain-tag",
        default="",
        help="If set, only cases with matching domain/domain_tag (e.g. finance_macro_b2b)",
    )
    args = ap.parse_args()
    if not args.matrix_input.is_file():
        print(json.dumps({"error": "missing_matrix"}))
        return 2

    src = json.loads(args.matrix_input.read_text(encoding="utf-8-sig"))
    all_cases = src.get("compression_cases") or []
    picked: list[dict[str, Any]] = []
    domain_filter = (args.domain_tag or "").strip()
    for c in all_cases:
        if domain_filter:
            dom = str(c.get("domain") or c.get("domain_tag") or "")
            if dom != domain_filter:
                continue
        raw = str(c.get("raw_text") or "")
        if len(raw.encode("utf-8")) < args.min_raw_bytes:
            continue
        picked.append(
            {
                "id": c.get("id"),
                "raw_text": raw,
                "domain": c.get("domain"),
                "source_path": c.get("source_path"),
            }
        )
        if len(picked) >= args.max_cases:
            break

    lens = [len(c["raw_text"].encode()) for c in picked]
    out = {
        "schema": "nextgen_longform_spine_bench_input_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "source_matrix": str(args.matrix_input.relative_to(ROOT)).replace("\\", "/"),
        "filter": {
            "min_raw_utf8_bytes": args.min_raw_bytes,
            "max_cases": args.max_cases,
            "domain_tag": domain_filter or None,
        },
        "case_count": len(picked),
        "raw_utf8_bytes": {
            "min": min(lens) if lens else 0,
            "max": max(lens) if lens else 0,
            "avg": round(sum(lens) / len(lens), 2) if lens else 0,
        },
        "compression_cases": picked,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"wrote": str(args.out_json), "case_count": len(picked), "bytes_avg": out["raw_utf8_bytes"]["avg"]},
            ensure_ascii=False,
        )
    )
    return 0 if picked else 1


if __name__ == "__main__":
    raise SystemExit(main())
