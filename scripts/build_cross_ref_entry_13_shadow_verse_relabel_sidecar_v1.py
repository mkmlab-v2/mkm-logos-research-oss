#!/usr/bin/env python3
"""ENTRY_13 shadow verse relabel sidecar (no CROSS_REF draft mutation) [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INTAKE = ROOT / "data/logos/manuscripts/evidence_intake/entry_12_13_external_witness_v1.json"
SIGNOFF = ROOT / "docs/final/artifacts/entry_13_commander_scholarly_promotion_signoff_v1_latest.json"
OUT_DEFAULT = ROOT / "reports/cross_ref_entry_13_shadow_verse_relabel_sidecar_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    intake = _load(INTAKE)
    signoff = _load(SIGNOFF)
    e13 = next((r for r in intake.get("witness_promotions") or [] if r.get("entry_id") == "ENTRY_13"), {})
    return {
        "schema": "cross_ref_entry_13_shadow_verse_relabel_sidecar_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "entry_id": "ENTRY_13",
        "cross_ref_bench_label": "Ps.5.2",
        "shadow_verse_anchor": e13.get("shadow_verse_anchor") or "Ps.5.8-9",
        "crosswalk_resolution": e13.get("crosswalk_resolution") or "shadow_rail_commander_accepted",
        "witness_id": (signoff.get("promoted_witness") or {}).get("witness_id") or e13.get("witness_id"),
        "scroll": e13.get("scroll"),
        "fragment": e13.get("fragment"),
        "line": e13.get("line"),
        "edition_ref": e13.get("edition_ref"),
        "note": (
            "CROSS_REF draft keeps Ps.5.2 bench label; shadow rail documents Ps 5:8-9 fragment anchor. "
            "No draft mutation."
        ),
        "track_wall": {
            "cross_ref_draft_mutation_forbidden": True,
            "logos_core_mutation_forbidden": True,
            "merge_into_canon_31k_41k": False,
        },
        "reproduce": "py scripts/build_cross_ref_entry_13_shadow_verse_relabel_sidecar_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "shadow_verse_anchor": doc.get("shadow_verse_anchor")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
