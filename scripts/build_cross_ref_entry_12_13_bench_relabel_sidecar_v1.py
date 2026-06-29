#!/usr/bin/env python3
"""ENTRY_12/13 bench relabel sidecar (no CROSS_REF draft mutation) [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "reports/cross_ref_entry_12_13_bench_relabel_sidecar_v1_latest.json"
MAP_4Q = ROOT / "reports/dss_4q_ps5_line_witness_map_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def build() -> dict[str, Any]:
    map4q = _load(MAP_4Q)
    return {
        "schema": "cross_ref_entry_12_13_bench_relabel_sidecar_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "track_wall": {
            "cross_ref_draft_mutation_forbidden": True,
            "logos_core_mutation_forbidden": True,
            "merge_into_canon_31k_41k": False,
        },
        "entries": [
            {
                "entry_id": "ENTRY_12",
                "canonical_ref": "Ps.4.6",
                "prior_satellite": "11Q5",
                "bench_status": "hypothesis_retired",
                "new_witness_rail": "mt_only",
                "note": "11Q5 does not physically contain Ps.4; Qumran Hebrew witness none in ETCBC.",
            },
            {
                "entry_id": "ENTRY_13",
                "canonical_ref": "Ps.5.2",
                "prior_satellite": "11Q5",
                "bench_status": "retargeted",
                "new_witness_rail": "4Q83_4Q98b_shadow",
                "new_satellite_scrolls": ["4Q83", "4Q98b", "4Q98"],
                "provisional_witness_rows": (map4q.get("summary") or {}).get("witness_rows"),
                "note": "11Q5 bench retired; shadow witnesses from Cave 4 psalms scrolls (provisional).",
            },
        ],
        "reproduce": "py scripts/build_cross_ref_entry_12_13_bench_relabel_sidecar_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "entries": len(doc["entries"]), "out": str(args.out.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
