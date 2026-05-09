#!/usr/bin/env python3
"""Build date-balanced non-synthetic news set from news_observation_v1_latest."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_IN = ART / "news_observation_v1_latest.jsonl"
DEFAULT_OUT = ART / "news_observation_v1_non_synthetic_date_balanced_latest.jsonl"
DEFAULT_META = ART / "news_observation_v1_non_synthetic_date_balanced_meta_latest.json"

SYNTHETIC_SOURCE_IDS = {"label_guided_seed", "manual_seed"}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build date-balanced non-synthetic news observation set.")
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--meta-json", type=Path, default=DEFAULT_META)
    ap.add_argument("--max-per-day", type=int, default=2)
    args = ap.parse_args()

    rows = _load_jsonl(args.input_jsonl)
    non_synth = [r for r in rows if str(r.get("source_id", "")) not in SYNTHETIC_SOURCE_IDS]
    non_synth.sort(key=lambda r: str(r.get("as_of_utc", "")))

    by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in non_synth:
        day = str(r.get("as_of_utc", ""))[:10]
        by_day[day].append(r)

    out_rows: list[dict[str, Any]] = []
    max_per_day = max(1, int(args.max_per_day))
    for day in sorted(by_day.keys()):
        out_rows.extend(by_day[day][:max_per_day])

    _write_jsonl(args.output_jsonl, out_rows)

    meta = {
        "schema": "news_observation_non_synthetic_date_balanced_meta_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "input_jsonl": str(args.input_jsonl).replace("\\", "/"),
        "output_jsonl": str(args.output_jsonl).replace("\\", "/"),
        "max_per_day": max_per_day,
        "input_row_count": len(rows),
        "input_non_synthetic_count": len(non_synth),
        "output_row_count": len(out_rows),
        "output_unique_days": len(by_day),
    }
    args.meta_json.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_jsonl": str(args.output_jsonl), "output_row_count": len(out_rows), "output_unique_days": len(by_day)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

