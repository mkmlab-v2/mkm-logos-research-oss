#!/usr/bin/env python3
"""Merge BigSet Tier-0 CSV batches — append by source_url with dedup (memory-light live accumulate).

Reproducible:
  py scripts/merge_bigset_tier0_csv_accumulate_v1.py \\
    --target docs/research/raw/bigset_benei_haelohim_cross_refs_tier0_v1.csv \\
    --batch docs/final/artifacts/bigset_tier0_live_batch_v1_latest.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.bigset_agent_bridge_v1 import (  # noqa: E402
    REQUIRED_COLUMNS,
    _normalize_rows,
    _read_csv_rows,
    _write_csv,
)

DEFAULT_ARTIFACT = ROOT / "docs/final/artifacts/bigset_tier0_csv_accumulate_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _source_key(row: dict[str, str]) -> str:
    return str(row.get("source_url") or "").strip().rstrip("/").lower()


def merge_accumulate(
    *,
    target_csv: Path,
    batch_csv: Path,
    dedupe_key: str = "source_url",
) -> dict[str, Any]:
    if not batch_csv.is_file():
        return {
            "ok": False,
            "error": "missing_batch_csv",
            "batch_csv": str(batch_csv),
        }

    existing: list[dict[str, str]] = []
    if target_csv.is_file():
        existing = _read_csv_rows(target_csv)

    batch_rows = _read_csv_rows(batch_csv)
    batch_rows, norm_notes = _normalize_rows(batch_rows)
    if dedupe_key != "source_url":
        raise ValueError("only source_url dedupe supported in v1")

    seen = {_source_key(r) for r in existing if _source_key(r)}
    appended: list[dict[str, str]] = []
    skipped_dup: list[str] = []

    for row in batch_rows:
        key = _source_key(row)
        if not key:
            continue
        if key in seen:
            skipped_dup.append(key)
            continue
        seen.add(key)
        appended.append(row)

    merged = existing + appended
    if merged:
        target_csv.parent.mkdir(parents=True, exist_ok=True)
        _write_csv(merged, target_csv)

    return {
        "ok": True,
        "target_csv": str(target_csv),
        "batch_csv": str(batch_csv),
        "rows_before": len(existing),
        "batch_rows": len(batch_rows),
        "rows_appended": len(appended),
        "rows_after": len(merged),
        "skipped_duplicate_source_urls": skipped_dup,
        "normalization_notes": norm_notes,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", type=Path, required=True, help="accumulated tier0 csv")
    ap.add_argument("--batch", type=Path, required=True, help="latest live batch csv (typically 1 row)")
    ap.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    args = ap.parse_args()

    target = args.target if args.target.is_absolute() else (ROOT / args.target)
    batch = args.batch if args.batch.is_absolute() else (ROOT / args.batch)

    result = merge_accumulate(target_csv=target, batch_csv=batch)
    doc = {
        "schema": "bigset_tier0_csv_accumulate_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        **result,
        "reproduce": (
            "py scripts/merge_bigset_tier0_csv_accumulate_v1.py "
            f"--target {target.relative_to(ROOT).as_posix()} "
            f"--batch {batch.relative_to(ROOT).as_posix()}"
        ),
    }
    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": result.get("ok"), "rows_after": result.get("rows_after"), **result}, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
