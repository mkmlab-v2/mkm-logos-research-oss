#!/usr/bin/env python3
"""Apply LogosEncoder reencode vectors to verse_decoded jsonl (B-track, with backup)."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.myeongni.gematria_myeongri_math_v1 import coerce_4d

JSONL = ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl"
ENCODER = ROOT / "reports/logos_4d_encoder_reencode_v1_latest.jsonl"
OUT_META = ROOT / "reports/logos_jsonl_4d_encoder_promotion_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_encoder(path: Path) -> dict[str, dict[str, float]]:
    m: dict[str, dict[str, float]] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            after = row.get("vector_4d_after")
            if vid and isinstance(after, dict):
                m[vid] = coerce_4d(after)
    return m


def apply(*, jsonl: Path, encoder: Path, dry_run: bool) -> dict:
    patch = _load_encoder(encoder)
    updated = 0
    total = 0
    tmp = jsonl.with_suffix(jsonl.suffix + ".promote_tmp")
    backup: Path | None = None
    if not dry_run:
        backup = jsonl.with_suffix(jsonl.suffix + f".bak_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(jsonl, backup)
    writer = (tmp.open("w", encoding="utf-8", newline="\n") if not dry_run else None)
    try:
        with jsonl.open(encoding="utf-8") as src:
            for line in src:
                total += 1
                row = json.loads(line)
                vid = str(row.get("verse_id") or "")
                if vid in patch:
                    v = patch[vid]
                    row["vector_4d"] = {k: round(v[k], 6) for k in v}
                    row["unified_4d_vector"] = dict(row["vector_4d"])
                    row["4d_promotion_v1"] = {
                        "source": "logos_encoder_reencode_v1",
                        "applied_at_utc": _utc(),
                        "hypothesis_tier": "B",
                    }
                    updated += 1
                if writer:
                    writer.write(json.dumps(row, ensure_ascii=False) + "\n")
    finally:
        if writer:
            writer.close()
    if not dry_run and writer:
        tmp.replace(jsonl)
    return {
        "jsonl_rows": total,
        "updated_rows": updated,
        "encoder_rows": len(patch),
        "backup_path": str(backup) if backup else None,
        "dry_run": dry_run,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", type=Path, default=JSONL)
    ap.add_argument("--encoder-jsonl", type=Path, default=ENCODER)
    ap.add_argument("--out-meta", type=Path, default=OUT_META)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.jsonl.is_file() or not args.encoder_jsonl.is_file():
        print(json.dumps({"ok": False, "error": "missing jsonl or encoder jsonl"}))
        return 2
    stats = apply(jsonl=args.jsonl, encoder=args.encoder_jsonl, dry_run=args.dry_run)
    meta = {
        "schema": "logos_jsonl_4d_encoder_promotion_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_wall": {"a_track_auto_promotion": False, "live_trading": False},
        "stats": stats,
    }
    if not args.dry_run:
        args.out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, **stats}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
