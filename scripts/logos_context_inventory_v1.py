#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Logos lane disk inventory — U3 lite_plus census (B-track, reproducible)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_context_inventory_v1_latest.json"
EXPECTATION_MATRIX = ROOT / "docs/final/artifacts/logos_expectation_vs_fact_matrix_v1_lite.md"
VERSION = "1.0.0"
SCHEMA = "logos_context_inventory_v1"

LOGOS_RE = re.compile(r"logos|bible|gematria|graphrag|topology_sidecar", re.IGNORECASE)

SCAN_ROOTS: tuple[tuple[str, Path, bool], ...] = (
    ("scripts", ROOT / "scripts", False),
    ("tests", ROOT / "tests", False),
    ("artifacts", ROOT / "docs/final/artifacts", False),
    ("reports", ROOT / "reports", True),
    ("schemas", ROOT / "docs/final/schemas", True),
    ("data", ROOT / "data/logos", True),
)

KEY_ANCHORS: tuple[tuple[str, str], ...] = (
    ("expectation_matrix_lite", "docs/final/artifacts/logos_expectation_vs_fact_matrix_v1_lite.md"),
    ("independent_lens_contract", "docs/final/artifacts/LOGOS_INDEPENDENT_LENS_V0_CONTRACT.json"),
    ("independent_lens_output", "docs/final/artifacts/logos_independent_lens_latest.json"),
    ("nl_fact_lock_guard", "docs/final/artifacts/notebooklm_lens_logos_nl_fact_lock_guard_v1_latest.md"),
    ("corpus_manifest", "docs/final/artifacts/logos_corpus_manifest_v1_latest.json"),
    ("vector_ann_lite", "docs/final/artifacts/logos_vector_index_ann_lite_v1_latest.json"),
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
        candidates = (p for p in root.rglob("*") if p.is_file() and LOGOS_RE.search(p.name))
    else:
        candidates = (p for p in root.iterdir() if p.is_file() and LOGOS_RE.search(p.name))
    rows: list[dict[str, Any]] = []
    for p in sorted(candidates, key=lambda x: _rel(x)):
        row: dict[str, Any] = {"bucket": bucket, "path": _rel(p), "exists": True}
        try:
            st = p.stat()
            row["bytes"] = int(st.st_size)
        except OSError as e:
            row["stat_error"] = str(e)
        rows.append(row)
    return rows


def _anchor_status() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for role, rel in KEY_ANCHORS:
        p = ROOT / rel
        out[role] = {"role": role, "path": rel, "exists": p.is_file()}
    return out


def build_inventory(*, generated_at_utc: str | None = None) -> dict[str, Any]:
    assets: list[dict[str, Any]] = []
    for bucket, root, recursive in SCAN_ROOTS:
        assets.extend(_scan_bucket(bucket, root, recursive))
    bucket_counts: dict[str, int] = {}
    for row in assets:
        b = row["bucket"]
        bucket_counts[b] = bucket_counts.get(b, 0) + 1
    primary_totals = {
        "scripts": bucket_counts.get("scripts", 0),
        "tests": bucket_counts.get("tests", 0),
        "artifacts": bucket_counts.get("artifacts", 0),
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": generated_at_utc or _utc_now(),
        "rail": "B_TRACK",
        "research_only": True,
        "send_gate": "HOLD",
        "gating_tag": "[NON_GATING]",
        "u3_tier": "lite_plus",
        "expectation_matrix_ref": _rel(EXPECTATION_MATRIX),
        "expectation_matrix_exists": EXPECTATION_MATRIX.is_file(),
        "summary": {
            "total_assets": len(assets),
            "primary_totals": primary_totals,
            "bucket_counts": bucket_counts,
        },
        "key_anchors": _anchor_status(),
        "assets": assets,
        "reproduce_command": "py scripts/logos_context_inventory_v1.py",
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
