#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Myeongni lane disk inventory — U3 lite anchor census (B-track, reproducible)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/myeongni_context_inventory_v1_latest.json"
EXPECTATION_MATRIX = ROOT / "docs/final/artifacts/myeongni_expectation_vs_fact_matrix_v1_lite.md"
VERSION = "1.0.0"
SCHEMA = "myeongni_context_inventory_v1"

MYEONGNI_RE = re.compile(
    r"myeongni|myeongri|manseryeok|saju|jijangan|daewoon|qiyun|십신|사주",
    re.IGNORECASE,
)

SCAN_ROOTS: tuple[tuple[str, Path, bool], ...] = (
    ("scripts", ROOT / "scripts", False),
    ("tests", ROOT / "tests", False),
    ("artifacts", ROOT / "docs/final/artifacts", False),
    ("reports", ROOT / "reports", True),
    ("data", ROOT / "data/myeongni", True),
)

KEY_ANCHORS: tuple[tuple[str, str], ...] = (
    ("expectation_matrix_lite", "docs/final/artifacts/myeongni_expectation_vs_fact_matrix_v1_lite.md"),
    ("independent_lens_contract", "docs/final/artifacts/MYEONGNI_INDEPENDENT_LENS_V0_CONTRACT.json"),
    ("independent_lens_output", "docs/final/artifacts/myeongni_independent_lens_latest.json"),
    ("conflict_runtime_mode", "reports/myeongni_conflict_arbitration_runtime_mode_latest.json"),
    ("conflict_policy", "data/myeongni/myeongni_conflict_arbitration_v1.json"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _scan_bucket(bucket: str, root: Path, recursive: bool) -> list[dict[str, Any]]:
    if not root.is_dir():
        return []
    if recursive:
        candidates = (p for p in root.rglob("*") if p.is_file() and MYEONGNI_RE.search(p.name))
    else:
        candidates = (p for p in root.iterdir() if p.is_file() and MYEONGNI_RE.search(p.name))
    return [{"bucket": bucket, "path": _rel(p), "exists": True} for p in sorted(candidates, key=_rel)]


def build_inventory(*, generated_at_utc: str | None = None) -> dict[str, Any]:
    assets: list[dict[str, Any]] = []
    for bucket, root, recursive in SCAN_ROOTS:
        assets.extend(_scan_bucket(bucket, root, recursive))
    bucket_counts: dict[str, int] = {}
    for row in assets:
        bucket_counts[row["bucket"]] = bucket_counts.get(row["bucket"], 0) + 1
    anchors = {
        role: {"role": role, "path": rel, "exists": (ROOT / rel).is_file()}
        for role, rel in KEY_ANCHORS
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": generated_at_utc or _utc_now(),
        "rail": "B_TRACK",
        "research_only": True,
        "send_gate": "HOLD",
        "u3_tier": "lite",
        "expectation_matrix_ref": _rel(EXPECTATION_MATRIX),
        "summary": {"total_assets": len(assets), "bucket_counts": bucket_counts},
        "key_anchors": anchors,
        "assets": assets,
        "reproduce_command": "py scripts/myeongni_context_inventory_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not EXPECTATION_MATRIX.is_file():
        print(f"MISSING expectation matrix: {EXPECTATION_MATRIX}", flush=True)
        return 2
    doc = build_inventory()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(json.dumps(doc["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
