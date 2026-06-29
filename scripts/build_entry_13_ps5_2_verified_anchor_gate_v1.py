#!/usr/bin/env python3
"""Gate for ENTRY_13 Ps.5.2 verified_anchor evidence packet (honest gap) [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "reports/entry_13_ps5_2_verified_anchor_evidence_packet_v1_latest.json"
CROSS = ROOT / "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json"
OUT_DEFAULT = ROOT / "docs/final/artifacts/entry_13_ps5_2_verified_anchor_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    pkt = _load(PACKET)
    cross = _load(CROSS)
    e13 = next((e for e in cross.get("entries") or [] if e.get("entry_id") == "ENTRY_13"), {})
    sat = str(e13.get("satellite_ref") or "")
    scan = pkt.get("witness_candidate_scan") or {}
    checks = {
        "packet_present": {"passed": pkt.get("schema") == "entry_13_ps5_2_verified_anchor_evidence_packet_v1"},
        "gap_honestly_documented": {"passed": pkt.get("verified_anchor_achieved") is False},
        "shadow_rail_separate": {"passed": bool((pkt.get("shadow_rail") or {}).get("shadow_verse_anchor"))},
        "external_qd_cited": {
            "passed": any(
                (s.get("source") == "Qumran-Digital 4Q98b") for s in pkt.get("external_sources") or []
            ),
        },
        "no_direct_line_candidates": {"passed": int(scan.get("direct_line_candidates") or 0) == 0},
        "cross_ref_not_verified_anchor": {
            "passed": "verified_anchor" not in sat and "commander_verified_shadow_witness" in sat,
        },
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "entry_13_ps5_2_verified_anchor_gate_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "verified_anchor_achieved": False,
        "gate_ok": gate_ok,
        "checks": checks,
        "promotion_blockers": pkt.get("promotion_blockers") or [],
        "reproduce": "py scripts/build_entry_13_ps5_2_verified_anchor_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "gate_ok": doc["gate_ok"], "verified_anchor_achieved": False}, ensure_ascii=False))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
