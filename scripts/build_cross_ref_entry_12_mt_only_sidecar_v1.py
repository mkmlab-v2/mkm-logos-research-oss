#!/usr/bin/env python3
"""ENTRY_12 mt_only witness rail sidecar (11Q5 bench retired) [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROMO_GATE = ROOT / "docs/final/artifacts/dss_line_witness_promotion_gate_v1_latest.json"
SCAN = ROOT / "reports/dss_line_witness_verification_scan_v1_latest.json"
OUT_DEFAULT = ROOT / "reports/cross_ref_entry_12_mt_only_sidecar_v1_latest.json"


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
    scan = _load(SCAN)
    promo = _load(PROMO_GATE)
    e12 = next((e for e in scan.get("entries") or [] if e.get("entry_id") == "ENTRY_12"), {})
    return {
        "schema": "cross_ref_entry_12_mt_only_sidecar_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "entry_id": "ENTRY_12",
        "canonical_ref": "Ps.4.6",
        "witness_rail": "mt_only",
        "qumran_hebrew_witness": "none_documented",
        "eleven_q5_bench_status": "hypothesis_retired",
        "rationale": (
            "11Q5 scroll witnesses Psalms 101+ per DJD IV; Ps.4.6 has no Qumran Hebrew line witness "
            "in local ETCBC or strict auto-scan (auto_verified=0)."
        ),
        "auto_scan_verified_count": e12.get("auto_verified_count"),
        "promotion_ok": promo.get("promotion_ok"),
        "track_wall": {
            "cross_ref_draft_mutation_forbidden": True,
            "logos_core_mutation_forbidden": True,
            "merge_into_canon_31k_41k": False,
        },
        "reproduce": "py scripts/build_cross_ref_entry_12_mt_only_sidecar_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "witness_rail": doc["witness_rail"], "out": str(args.out.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
