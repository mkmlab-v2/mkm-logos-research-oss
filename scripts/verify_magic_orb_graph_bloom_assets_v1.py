#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify magic_orb insight JSON assets include graph_bloom ([HYPO] B-track gate)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PATHS = [
    ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json",
    ROOT / "projects/mkm/mkm-life/public/data/magic_orb_question_insight_v1_latest.json",
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _check_insight(path: Path, min_nodes: int) -> list[str]:
    errs: list[str] = []
    doc = _load(path)
    if doc.get("schema") != "magic_orb_question_insight_v1":
        errs.append(f"{path}: schema not magic_orb_question_insight_v1")
        return errs
    gb = doc.get("graph_bloom")
    if not isinstance(gb, dict) or gb.get("schema") != "magic_orb_graph_bloom_v1":
        errs.append(f"{path}: missing graph_bloom")
        return errs
    n = len(gb.get("nodes") or [])
    if n < min_nodes:
        errs.append(f"{path}: graph_bloom nodes {n} < {min_nodes}")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-nodes", type=int, default=20)
    ap.add_argument("--by-query-dir", type=Path, default=ROOT / "projects/mkm/mkm-life/public/data/magic_orb_insight_by_query")
    ap.add_argument("--insight", type=Path, action="append", default=[])
    args = ap.parse_args()

    paths = list(args.insight) or []
    if not paths:
        paths = [p for p in DEFAULT_PATHS if p.is_file()]

    errs: list[str] = []
    for p in paths:
        if p.is_file():
            errs.extend(_check_insight(p, args.min_nodes))

    by_query = args.by_query_dir
    if by_query.is_dir():
        for f in sorted(by_query.glob("*.json")):
            errs.extend(_check_insight(f, args.min_nodes))

    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "checked_insight_files": len(paths),
                "by_query_files": len(list(by_query.glob("*.json"))) if by_query.is_dir() else 0,
                "min_nodes": args.min_nodes,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
