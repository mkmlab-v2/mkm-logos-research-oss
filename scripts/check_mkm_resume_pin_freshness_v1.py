#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check resume pin freshness + CENTRAL checkpoint contradictions (P0.3).

  py scripts/check_mkm_resume_pin_freshness_v1.py
  py scripts/check_mkm_resume_pin_freshness_v1.py --strict
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from mkm_ops_memory_index_lib_v1 import (  # noqa: E402
    DEFAULT_INDEX_PATH,
    nodes_for_resume,
)
from mkm_resume_pin_freshness_v1 import (  # noqa: E402
    annotate_ops_pins_freshness,
    build_freshness_report,
    load_policy,
    write_freshness_latest,
)

DEFAULT_LATEST = ROOT / "docs" / "final" / "artifacts" / "mkm_resume_pin_freshness_v1_latest.json"


def _load_index(root: Path) -> dict:
    path = root / DEFAULT_INDEX_PATH.relative_to(ROOT)
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _default_pins(root: Path) -> list[dict]:
    index = _load_index(root)
    if not index:
        return []
    routed = list(nodes_for_resume(index, top_n=8, lane=None, root=root, commander_default=True))
    return [
        {
            "node_id": node_id,
            "essence": node.get("essence"),
            "must_keep_tags": node.get("must_keep_tags") or [],
            "file_path": node.get("file_path"),
        }
        for node_id, node in routed
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--out", type=Path, default=DEFAULT_LATEST)
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any stale_advisory, contradiction, or l0_l2_claim_gap (advisory gate).",
    )
    ap.add_argument("--dry-run", action="store_true", help="Validate only; do not write artifact.")
    args = ap.parse_args(argv)

    root = args.workspace_root.resolve()
    policy = load_policy()
    pins = _default_pins(root)
    if not pins:
        print("WARN: no ops pins (index missing?) — empty freshness report", file=sys.stderr)

    enriched, contradictions, l0_l2_gaps = annotate_ops_pins_freshness(
        pins, root, policy=policy
    )
    report = build_freshness_report(
        enriched,
        contradictions,
        l0_l2_claim_gaps=l0_l2_gaps,
        policy=policy,
    )

    stale = int(report["advisory_summary"]["stale_pin_count"])
    coll = int(report["advisory_summary"]["contradiction_count"])
    gaps = int(report["advisory_summary"]["l0_l2_claim_gap_count"])
    print(
        f"pin_freshness: pins={len(enriched)} stale={stale} contradictions={coll} "
        f"l0_l2_gaps={gaps} send_gate=HOLD research_only=True"
    )
    for row in report.get("pins") or []:
        if row.get("stale_advisory"):
            print(
                f"  STALE {row['node_id']}: age_days={row['age_days']} "
                f"> max_age_days={row['max_age_days']} ({row['age_source']})"
            )
    for hit in contradictions[:5]:
        print(
            f"  CONTRADICT {hit['collision_reason']}: "
            f"{hit['newer_stamp_utc']} vs {hit['older_stamp_utc']}"
        )
    for gap in l0_l2_gaps[:8]:
        print(
            f"  L0_L2_GAP {gap.get('gap_reason')}: {gap.get('node_id')} "
            f"file={gap.get('file_path') or '(none)'}"
        )

    if not args.dry_run:
        write_freshness_latest(report, args.out)
        print(f"WROTE: {args.out}")

    if args.strict and (stale > 0 or coll > 0 or gaps > 0):
        print(
            "FAIL: strict — stale pins, checkpoint contradictions, or l0_l2 claim gaps",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
