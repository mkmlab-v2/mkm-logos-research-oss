#!/usr/bin/env python3
"""Attested-only joint benchmark snapshot (excludes dummy tier) [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "data/myeongni/sasang_saju_joint_benchmark_v1.jsonl"
SNAPSHOT = ROOT / "data/myeongni/sasang_saju_joint_benchmark_attested_only_v1.jsonl"
OUT = ROOT / "reports/sasang_joint_benchmark_attested_only_snapshot_v1_latest.json"


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


def build(dataset: Path, snapshot: Path) -> dict[str, Any]:
    rows: list[str] = []
    ids: list[str] = []
    commander_attested_ids: list[str] = []
    if dataset.is_file():
        for line in dataset.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if _is_dummy(row):
                continue
            rows.append(line)
            pid = str(row.get("person_id") or "")
            ids.append(pid)
            prov = str(row.get("provenance") or "")
            if "commander_attested" in prov:
                commander_attested_ids.append(pid)

    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    snapshot_ok = len(ids) >= 5
    return {
        "schema": "sasang_joint_benchmark_attested_only_snapshot_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "rows_attested": len(ids),
        "person_ids": ids,
        "commander_attested_ids": commander_attested_ids,
        "snapshot_jsonl": str(snapshot.resolve()).replace("\\", "/"),
        "snapshot_ok": snapshot_ok,
        "reproduce": "py scripts/build_sasang_joint_benchmark_attested_only_snapshot_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", type=Path, default=BENCH)
    ap.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build(args.dataset, args.snapshot)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["snapshot_ok"], "rows_attested": doc["rows_attested"]}))
    return 0 if doc["snapshot_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
