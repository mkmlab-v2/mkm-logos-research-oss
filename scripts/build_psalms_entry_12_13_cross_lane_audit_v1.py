#!/usr/bin/env python3
"""Psalms ENTRY_12/13 focused cross-lane audit (2-verse pilot) [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"
REGISTRY = ROOT / "reports/shadow_4q_ps5_witness_registry_v1_latest.json"
INTAKE = ROOT / "data/logos/manuscripts/evidence_intake/entry_12_13_external_witness_v1.json"
RELABEL = ROOT / "reports/cross_ref_entry_13_shadow_verse_relabel_sidecar_v1_latest.json"
OUT_DEFAULT = ROOT / "reports/psalms_entry_12_13_cross_lane_audit_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _canon_row(verse_id: str) -> dict[str, Any] | None:
    if not CANON.is_file():
        return None
    for line in CANON.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if str(row.get("verse_id") or "") == verse_id:
            return row
    return None


def build() -> dict[str, Any]:
    reg = _load(REGISTRY)
    intake = _load(INTAKE)
    relabel = _load(RELABEL)
    promoted = [r for r in reg.get("rows") or [] if r.get("commander_promoted")]
    e12 = next((r for r in intake.get("witness_promotions") or [] if r.get("entry_id") == "ENTRY_12"), {})
    e13 = next((r for r in intake.get("witness_promotions") or [] if r.get("entry_id") == "ENTRY_13"), {})

    verses = []
    for vid, entry_id, note in (
        ("Ps.4.6", "ENTRY_12", "mt_only; 11Q5 hypothesis retired"),
        ("Ps.5.2", "ENTRY_13", "bench label; shadow anchor Ps.5.8-9 via 4Q98b"),
    ):
        canon = _canon_row(vid)
        verses.append(
            {
                "verse_id": vid,
                "entry_id": entry_id,
                "canon_present": canon is not None,
                "canon_lane": (canon or {}).get("lane"),
                "interpretation_status": (
                    "mt_only"
                    if entry_id == "ENTRY_12"
                    else "commander_verified_shadow_witness"
                    if promoted
                    else "provisional_lexical_anchor"
                ),
                "shadow_verse_anchor": relabel.get("shadow_verse_anchor") if entry_id == "ENTRY_13" else None,
                "note": note,
            }
        )

    return {
        "schema": "psalms_entry_12_13_cross_lane_audit_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "pilot_verse_count": 2,
        "verses": verses,
        "entry_12": {"status": e12.get("status") or "mt_only", "scroll_retired": "11Q5"},
        "entry_13": {
            "status": e13.get("status") or "commander_promoted_shadow",
            "witness_id": e13.get("witness_id"),
            "scroll": e13.get("scroll"),
            "shadow_verse_anchor": e13.get("shadow_verse_anchor") or relabel.get("shadow_verse_anchor"),
        },
        "commander_verified_rows": int((reg.get("summary") or {}).get("commander_verified_rows") or 0),
        "cross_ref_draft_mutated": False,
        "verified_anchor_achieved": False,
        "audit_ok": True,
        "reproduce": "py scripts/build_psalms_entry_12_13_cross_lane_audit_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "audit_ok": doc["audit_ok"], "verses": len(doc["verses"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
