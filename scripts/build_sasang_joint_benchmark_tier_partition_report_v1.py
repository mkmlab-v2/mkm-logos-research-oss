#!/usr/bin/env python3
"""Benchmark tier partition manifest: dummy vs attested (non-destructive) [HYPO]."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "data/myeongni/sasang_saju_joint_benchmark_v1.jsonl"
ARCHIVE = ROOT / "data/myeongni/sasang_saju_joint_benchmark_dummy_archive_v1.jsonl"
OUT = ROOT / "reports/sasang_joint_benchmark_tier_partition_v1_latest.json"


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
    dummy_ids: list[str] = []
    attested_ids: list[str] = []
    tiers: defaultdict[str, list[str]] = defaultdict(list)

    if BENCH.is_file():
        for line in BENCH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            pid = str(row.get("person_id") or "")
            tier = str(row.get("benchmark_tier") or "unknown")
            tiers[tier].append(pid)
            if _is_dummy(row):
                dummy_ids.append(pid)
            else:
                attested_ids.append(pid)

    archive_dummy_ids: list[str] = []
    if ARCHIVE.is_file():
        for line in ARCHIVE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            archive_dummy_ids.append(str(row.get("person_id") or ""))

    dummy_isolated = len(dummy_ids) == 0 and len(archive_dummy_ids) >= 1
    partition_ok = len(attested_ids) >= 5 and (len(dummy_ids) >= 1 or dummy_isolated)
    return {
        "schema": "sasang_joint_benchmark_tier_partition_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_destructive": True,
        "rows_total": len(dummy_ids) + len(attested_ids),
        "dummy_tier": {
            "count": len(dummy_ids),
            "person_ids": dummy_ids,
            "label": "hypo_fixture_only",
        },
        "dummy_archive_tier": {
            "count": len(archive_dummy_ids),
            "person_ids": archive_dummy_ids,
            "label": "archive_isolated_fixture",
        },
        "dummy_isolated_in_archive": dummy_isolated,
        "attested_tier": {
            "count": len(attested_ids),
            "person_ids": attested_ids,
            "label": "curator_attested_or_public_provenance",
        },
        "benchmark_tier_counts": {k: len(v) for k, v in tiers.items()},
        "partition_ok": partition_ok,
        "partition_status": (
            "isolated_manifest_ok" if partition_ok else "incomplete"
        ),
        "benchmark_jsonl": str(BENCH).replace("\\", "/"),
        "archive_jsonl": str(ARCHIVE).replace("\\", "/"),
        "reproduce": "py scripts/build_sasang_joint_benchmark_tier_partition_report_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["partition_ok"],
                "attested": doc["attested_tier"]["count"],
                "dummy": doc["dummy_tier"]["count"],
            }
        )
    )
    return 0 if doc["partition_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
