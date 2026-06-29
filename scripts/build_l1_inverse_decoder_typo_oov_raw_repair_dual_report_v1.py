#!/usr/bin/env python3
"""Dual-report raw(exact) vs operational(recovery) from typo/oov bucket eval (research_only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
IN_DEFAULT = ART / "l1_inverse_decoder_typo_oov_bucket_eval_v1_latest.json"
OUT_DEFAULT = ART / "l1_inverse_decoder_typo_oov_raw_repair_dual_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _dual_block(arm_row: dict[str, Any]) -> dict[str, Any]:
    raw_exact = float(arm_row["avg_exact_restore_rate"])
    repair_recovery = float(arm_row["avg_recovery_rate"])
    return {
        "raw": {
            "exact_restore_rate": raw_exact,
            "label": "decoder exact match (base model path)",
        },
        "repair_v2": {
            "recovery_rate": repair_recovery,
            "label": "operational (post-decoder recovery metric; not compression repair_v2)",
        },
        "delta": {
            "recovery_minus_exact": repair_recovery - raw_exact,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in-json", type=Path, default=IN_DEFAULT)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    src_path = args.in_json if args.in_json.is_absolute() else ROOT / args.in_json
    doc = json.loads(src_path.read_text(encoding="utf-8"))

    buckets: dict[str, Any] = {}
    for bucket, block in doc.get("results", {}).items():
        per_arm = []
        for row in block.get("per_arm", []):
            per_arm.append(
                {
                    "arm": row["arm"],
                    "decoder_path_sample": row.get("decoder_path_sample"),
                    **_dual_block(row),
                }
            )
        buckets[bucket] = {
            "recommended_arm": block.get("recommended_arm"),
            "per_arm": per_arm,
        }

    out_doc = {
        "schema": "l1_inverse_decoder_typo_oov_raw_repair_dual_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "source": str(src_path),
        "note": "repair_v2 field maps to L1 recovery_rate; compression-layer repair_v2 is a separate pipeline.",
        "buckets": buckets,
    }

    out_path = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
