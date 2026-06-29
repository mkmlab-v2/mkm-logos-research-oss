#!/usr/bin/env python3
"""Convert encoder reencode JSONL to pipeline4 patch rows (B-track)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENC = ROOT / "reports/logos_4d_encoder_reencode_v1_latest.jsonl"
OUT = ROOT / "reports/logos_4d_encoder_apply_patch_v1_latest.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-jsonl", type=Path, default=ENC)
    ap.add_argument("--out-jsonl", type=Path, default=OUT)
    args = ap.parse_args()
    n = 0
    with args.in_jsonl.open(encoding="utf-8") as src, args.out_jsonl.open("w", encoding="utf-8") as dst:
        for line in src:
            row = json.loads(line)
            after = row.get("vector_4d_after")
            vid = str(row.get("verse_id") or "")
            if not vid or not isinstance(after, dict):
                continue
            dst.write(
                json.dumps(
                    {
                        "verse_id": vid,
                        "patch_status": "proposed_pipeline4_from_logos_encoder",
                        "pipeline4_vector_4d_after": after,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            n += 1
    print(json.dumps({"ok": True, "rows": n, "out": str(args.out_jsonl)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
