#!/usr/bin/env python3
"""Produce DSS/Apocrypha shadow-lane pilot plan (design artifact, non-exec)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "reports/dss_apocrypha_shadow_lane_pilot_plan_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build() -> dict:
    return {
        "schema": "dss_apocrypha_shadow_lane_pilot_plan_v1",
        "generated_at_utc": _utc(),
        "non_gating": True,
        "research_only": True,
        "track_wall": {
            "track_a_bridge": False,
            "live_trading_bridge": False,
            "logos_core_mutation_forbidden": True,
        },
        "lane_design": {
            "name": "dss_apocrypha_shadow_lane",
            "goal": "Coverage/alignment measurement without modifying core 31k/41k production rails.",
            "inputs": [
                "data/logos/manuscripts/dss_parsed_enriched.jsonl",
                "docs/final/artifacts/logos_apocrypha_bootstrap_manifest_v1_latest.json",
            ],
            "outputs": [
                "reports/dss_shadow_alignment_v1_latest.json",
                "reports/apocrypha_shadow_alignment_v1_latest.json",
            ],
        },
        "phases": [
            {"id": "P0", "title": "Ingest inventory + schema normalization", "done_when": "row_count, null-rate, id contract reported"},
            {"id": "P1", "title": "31k/41k overlap coverage", "done_when": "shared term/verse coverage metrics emitted"},
            {"id": "P2", "title": "Shadow-only retrieval probe", "done_when": "retrieval metrics stored as non-gating appendix"},
            {"id": "P3", "title": "Human review packet", "done_when": "no direct bridge claims; appendix-only"},
        ],
        "no_go": [
            "No Track A policy mutation",
            "No live trigger from DSS/apocrypha signals",
            "No external headline claim without separate legal/ops gate",
        ],
        "reproduce": "py scripts/build_dss_apocrypha_shadow_lane_pilot_plan_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
