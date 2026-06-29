#!/usr/bin/env python3
"""Benchmark JSONL composition report: curated vs dummy vs literature tiers [HYPO]."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "data/myeongni/sasang_saju_joint_benchmark_v1.jsonl"
OUT = ROOT / "reports/sasang_joint_benchmark_composition_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_dummy(row: dict[str, Any]) -> bool:
    pid = str(row.get("person_id") or "")
    disp = str(row.get("display_name") or "")
    if "dummy" in pid.lower() or "dummy" in disp.lower():
        return True
    if "DUMMYCSV" in pid or "DUMMYJSONL" in pid:
        return True
    if "[DUMMY]" in disp:
        return True
    return False


def build() -> dict[str, Any]:
    tiers: Counter[str] = Counter()
    dummy = 0
    non_dummy = 0
    with_birth = 0
    rows = 0
    if BENCH.is_file():
        for line in BENCH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            rows += 1
            tiers[str(row.get("benchmark_tier") or "unknown")] += 1
            if _is_dummy(row):
                dummy += 1
            else:
                non_dummy += 1
            br = row.get("birth_resolution")
            if isinstance(br, dict) and str(br.get("birth_instant_utc") or "").strip():
                with_birth += 1
    return {
        "schema": "sasang_joint_benchmark_composition_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "rows_total": rows,
        "rows_dummy": dummy,
        "rows_non_dummy": non_dummy,
        "rows_with_birth": with_birth,
        "benchmark_tier_counts": dict(tiers),
        "composition_ok": non_dummy >= 1 and rows >= 1,
        "artifact_paths": {"benchmark_jsonl": str(BENCH).replace("\\", "/")},
        "reproduce": "py scripts/build_sasang_joint_benchmark_composition_report_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["composition_ok"], "rows_non_dummy": doc["rows_non_dummy"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
