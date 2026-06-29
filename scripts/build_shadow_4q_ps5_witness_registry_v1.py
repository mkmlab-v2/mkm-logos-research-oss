#!/usr/bin/env python3
"""Shadow registry for 4Q Ps.5 line witnesses (post-promotion aware) [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.shadow_lane_gematria_common_v1 import line_witness_numeric_eligible, load_json

MAP = ROOT / "reports/dss_4q_ps5_line_witness_map_v1_latest.json"
INTAKE = ROOT / "data/logos/manuscripts/evidence_intake/entry_12_13_external_witness_v1.json"
SIGNOFF = ROOT / "docs/final/artifacts/entry_13_commander_scholarly_promotion_signoff_v1_latest.json"
OUT_DEFAULT = ROOT / "reports/shadow_4q_ps5_witness_registry_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _intake_entry_13(intake: dict[str, Any]) -> dict[str, Any]:
    for row in intake.get("witness_promotions") or []:
        if row.get("entry_id") == "ENTRY_13":
            return row
    return {}


def build() -> dict[str, Any]:
    wmap = load_json(MAP)
    intake = load_json(INTAKE)
    signoff = load_json(SIGNOFF)
    e13 = _intake_entry_13(intake)
    shadow_anchor = str(e13.get("shadow_verse_anchor") or "Ps.5.8-9")
    rows: list[dict[str, Any]] = []
    numeric_eligible = 0
    commander_verified = 0
    canon_g = wmap.get("canon_gematria") or {}
    canon_hebrew = int(canon_g.get("hebrew_value") or 0)
    for witness in wmap.get("witnesses") or []:
        g = witness.get("gematria") or {}
        status = str(witness.get("mapping_status") or "")
        scroll = str(witness.get("scroll") or "")
        wid = str(witness.get("witness_id") or "")
        eligible = line_witness_numeric_eligible(gematria=g, mapping_status=status, scroll=scroll)
        is_commander = status.startswith("commander_verified")
        if eligible:
            numeric_eligible += 1
        if is_commander:
            commander_verified += 1
        hebrew_val = int(g.get("hebrew_value") or 0)
        rows.append(
            {
                "registry_id": f"witness:{wid}",
                "witness_id": wid,
                "entry_id": "ENTRY_13",
                "canon_verse_id": "Ps.5.2",
                "shadow_verse_anchor": shadow_anchor if is_commander else None,
                "lane": "dss",
                "scroll": scroll,
                "line": witness.get("line"),
                "gematria": g,
                "mapping_status": status,
                "commander_promoted": is_commander,
                "numeric_comparison_eligible": eligible,
                "hebrew_delta_vs_canon": hebrew_val - canon_hebrew if is_commander else None,
                "informational_delta_note": (
                    "shadow witness gematria vs MT Ps.5.2 bench label — not numeric gate eligible"
                    if is_commander
                    else None
                ),
                "non_gating": True,
                "research_only": True,
                "writes_canon": False,
            }
        )
    return {
        "schema": "shadow_4q_ps5_witness_registry_v1",
        "version": "1.1.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "shadow_verse_anchor": shadow_anchor,
        "commander_signoff_ok": signoff.get("promotion_ok") is True,
        "summary": {
            "registry_rows": len(rows),
            "commander_verified_rows": commander_verified,
            "provisional_rows": len(rows) - commander_verified,
            "numeric_comparison_eligible_rows": numeric_eligible,
        },
        "rows": rows,
        "reproduce": "py scripts/build_shadow_4q_ps5_witness_registry_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sm = doc["summary"]
    ok = int(sm.get("registry_rows") or 0) >= 4 and int(sm.get("commander_verified_rows") or 0) >= 1
    print(json.dumps({"ok": ok, "summary": sm}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
