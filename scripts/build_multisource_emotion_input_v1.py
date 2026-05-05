#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List


def _iter_jsonl(path: Path) -> Iterable[dict]:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except Exception:
            continue
        if isinstance(item, dict):
            yield item


def _event_id(row: dict) -> str:
    return str(row.get("seed_event_id") or row.get("event_id") or "").strip()


def _is_compatible(row: dict) -> bool:
    metrics = row.get("metrics")
    return isinstance(metrics, dict) and ("panic_ratio" in metrics) and ("fomo_index" in metrics)


def merge(primary: Path, extras: List[Path]) -> List[dict]:
    merged: Dict[str, dict] = {}

    for row in _iter_jsonl(primary):
        if not _is_compatible(row):
            continue
        key = _event_id(row)
        if not key:
            continue
        merged[key] = row

    for src in extras:
        if not src.is_file():
            continue
        for row in _iter_jsonl(src):
            if not _is_compatible(row):
                continue
            key = _event_id(row)
            if not key:
                continue
            # primary keeps precedence on collisions.
            if key not in merged:
                merged[key] = row

    rows = list(merged.values())
    rows.sort(key=lambda r: str(r.get("timestamp_utc", "")))
    return rows


def main() -> int:
    p = argparse.ArgumentParser(description="Merge multi-source emotion JSONL inputs.")
    p.add_argument("--primary-jsonl", type=Path, required=True)
    p.add_argument("--extra-jsonl", type=Path, action="append", default=[])
    p.add_argument("--out-jsonl", type=Path, required=True)
    args = p.parse_args()

    rows = merge(args.primary_jsonl, args.extra_jsonl)
    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"WROTE: {args.out_jsonl} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

