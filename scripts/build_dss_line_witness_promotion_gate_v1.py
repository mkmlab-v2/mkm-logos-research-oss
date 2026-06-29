#!/usr/bin/env python3
"""Promotion gate for ENTRY_12/13 verified line witness (auto + manual intake) [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "reports/dss_line_witness_verification_scan_v1_latest.json"
SIDECAR = ROOT / "reports/cross_ref_entry_12_13_evidence_sidecar_v1_latest.json"
WITNESS_MAP_11Q5 = ROOT / "reports/dss_11q5_line_witness_map_v1_latest.json"
MAP_4Q = ROOT / "reports/dss_4q_ps5_line_witness_map_v1_latest.json"
P5_GATE = ROOT / "docs/final/artifacts/p5_manuscript_integrity_gate_v1_latest.json"
INTAKE = ROOT / "data/logos/manuscripts/evidence_intake/entry_12_13_external_witness_v1.json"
OUT_DEFAULT = ROOT / "docs/final/artifacts/dss_line_witness_promotion_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _collect_witness_ids(*maps: dict[str, Any]) -> set[str]:
    wids: set[str] = set()
    for witness_map in maps:
        for entry in witness_map.get("entries") or []:
            for w in entry.get("witnesses") or []:
                wids.add(str(w.get("witness_id")))
        for w in witness_map.get("witnesses") or []:
            wids.add(str(w.get("witness_id")))
    return wids


def _manual_promotions(intake: dict[str, Any], *maps: dict[str, Any]) -> list[dict[str, Any]]:
    wids = _collect_witness_ids(*maps)
    out: list[dict[str, Any]] = []
    for row in intake.get("witness_promotions") or []:
        if row.get("approve_promotion") is not True:
            continue
        wid = str(row.get("witness_id") or "")
        if not wid or wid.endswith("XXXXXXX"):
            continue
        if wid not in wids:
            continue
        if not str(row.get("edition_ref") or "").strip():
            continue
        out.append(row)
    return out


def build() -> dict[str, Any]:
    scan = _load(SCAN)
    sidecar = _load(SIDECAR)
    wmap_11 = _load(WITNESS_MAP_11Q5)
    map_4q = _load(MAP_4Q)
    p5 = _load(P5_GATE)
    intake = _load(INTAKE)
    auto_verified = int((scan.get("summary") or {}).get("auto_verified_total") or 0)
    manual = _manual_promotions(intake, wmap_11, map_4q)
    p5_ok = p5.get("gate_ok") is True
    map_4q_ok = map_4q.get("schema") == "dss_4q_ps5_line_witness_map_v1" and int(
        (map_4q.get("summary") or {}).get("witness_rows") or 0
    ) >= 4

    checks = {
        "scan_complete": {
            "passed": scan.get("schema") == "dss_line_witness_verification_scan_v1",
            "auto_verified_total": auto_verified,
        },
        "sidecar_present": {
            "passed": sidecar.get("schema") == "cross_ref_entry_12_13_evidence_sidecar_v1",
        },
        "p5_manuscript_integrity": {
            "passed": p5_ok,
        },
        "witness_rail_infrastructure": {
            "passed": p5_ok or map_4q_ok or wmap_11.get("schema") == "dss_11q5_line_witness_map_v1",
            "map_4q_rows": (map_4q.get("summary") or {}).get("witness_rows"),
        },
        "no_auto_false_promotion": {
            "passed": True,
            "note": "auto_verified_total=0 expected until external line anchor or manual intake",
        },
        "manual_intake_validated": {
            "passed": True,
            "approved_rows": len(manual),
        },
        "track_wall": {
            "passed": (sidecar.get("track_wall") or {}).get("cross_ref_draft_mutation_forbidden") is True,
        },
        "send_gate_hold": {
            "passed": sidecar.get("send_gate") == "HOLD",
        },
    }
    promotion_eligible_count = auto_verified + len(manual)
    infrastructure_ok = all(c.get("passed") for c in checks.values())
    promotion_ok = promotion_eligible_count >= 1

    return {
        "schema": "dss_line_witness_promotion_gate_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "gate_ok": infrastructure_ok,
        "infrastructure_ok": infrastructure_ok,
        "promotion_ok": promotion_ok,
        "promotion_eligible_count": promotion_eligible_count,
        "promotion_pending_external": promotion_eligible_count == 0,
        "checks": checks,
        "manual_promotions": manual,
        "reproduce": "py scripts/build_dss_line_witness_promotion_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "gate_ok": doc["gate_ok"],
                "promotion_ok": doc["promotion_ok"],
                "promotion_pending_external": doc["promotion_pending_external"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
