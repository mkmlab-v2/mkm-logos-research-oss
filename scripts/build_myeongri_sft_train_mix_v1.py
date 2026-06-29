#!/usr/bin/env python3
"""Build mixed SFT train JSONL (base + hard-negative upsample)."""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = ROOT / "data/training/myeongri_deterministic_lora_sft_compact_qwen_train_v2.jsonl"
DEFAULT_HN = ROOT / "data/training/myeongri_deterministic_lora_hard_negative_sft_v1.jsonl"
DEFAULT_OUT = ROOT / "data/training/myeongri_deterministic_lora_sft_mix_v1.jsonl"
DEFAULT_MANIFEST = ROOT / "reports/myeongri_sft_mix_manifest_v1_latest.json"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-jsonl", type=Path, default=DEFAULT_BASE)
    ap.add_argument("--hard-negative-jsonl", type=Path, default=DEFAULT_HN)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--hard-negative-weight", type=float, default=2.0)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    if not args.base_jsonl.is_file():
        raise SystemExit(f"missing base jsonl: {args.base_jsonl}")
    if not args.hard_negative_jsonl.is_file():
        raise SystemExit(f"missing hard-negative jsonl: {args.hard_negative_jsonl}")

    base_rows = _load_jsonl(args.base_jsonl)
    hn_rows_raw = _load_jsonl(args.hard_negative_jsonl)
    # normalize hard-negative row to base train row shape
    hn_rows = [{"instruction": r.get("instruction"), "output": r.get("output")} for r in hn_rows_raw]
    hn_rows = [r for r in hn_rows if isinstance(r.get("instruction"), str) and isinstance(r.get("output"), str)]

    rng = random.Random(args.seed)
    upsample_n = int(round(len(hn_rows) * args.hard_negative_weight))
    hn_upsampled = [rng.choice(hn_rows) for _ in range(upsample_n)] if hn_rows and upsample_n > 0 else []

    mixed = list(base_rows) + hn_upsampled
    rng.shuffle(mixed)

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("w", encoding="utf-8") as f:
        for r in mixed:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    reason_counts = Counter(r.get("hard_negative_reason", "unknown") for r in hn_rows_raw)
    manifest = {
        "schema": "myeongri_sft_mix_manifest_v1",
        "base_jsonl": str(args.base_jsonl).replace("\\", "/"),
        "hard_negative_jsonl": str(args.hard_negative_jsonl).replace("\\", "/"),
        "out_jsonl": str(args.out_jsonl).replace("\\", "/"),
        "hard_negative_weight": args.hard_negative_weight,
        "seed": args.seed,
        "counts": {
            "base_rows": len(base_rows),
            "hard_negative_rows": len(hn_rows),
            "hard_negative_upsampled_rows": len(hn_upsampled),
            "total_rows": len(mixed),
        },
        "hard_negative_reason_counts": dict(reason_counts),
        "track_wall": {"research_only": True, "a_track_auto_promotion": False, "live_trading": False},
    }
    args.manifest_json.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "out_jsonl": str(args.out_jsonl), "total_rows": len(mixed)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

