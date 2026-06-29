#!/usr/bin/env python3
"""Shadow line witness registry from 11Q5 map (appendix-side only) [HYPO]."""

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

WITNESS_MAP = ROOT / "reports/dss_11q5_line_witness_map_v1_latest.json"
OUT_DEFAULT = ROOT / "reports/shadow_line_witness_registry_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build() -> dict[str, Any]:
    wmap = load_json(WITNESS_MAP)
    rows: list[dict[str, Any]] = []
    numeric_eligible = 0
    for entry in wmap.get("entries") or []:
        entry_id = entry.get("entry_id")
        canon_vid = entry.get("canon_verse_id")
        for witness in entry.get("witnesses") or []:
            g = witness.get("gematria") or {}
            status = str(witness.get("mapping_status") or "")
            scroll = str(witness.get("scroll") or "11Q5")
            eligible = line_witness_numeric_eligible(gematria=g, mapping_status=status, scroll=scroll)
            if eligible:
                numeric_eligible += 1
            canon_g = entry.get("canon_gematria") or {}
            rows.append(
                {
                    "registry_id": f"witness:{witness.get('witness_id')}",
                    "witness_id": witness.get("witness_id"),
                    "entry_id": entry_id,
                    "canon_verse_id": canon_vid,
                    "lane": "dss",
                    "scroll": scroll,
                    "line": witness.get("line"),
                    "gematria": g,
                    "mapping_score": witness.get("mapping_score"),
                    "mapping_status": status,
                    "comparison_type": witness.get("comparison_type"),
                    "numeric_comparison_eligible": eligible,
                    "hebrew_delta_vs_canon": int(g.get("hebrew_value") or 0) - int(canon_g.get("hebrew_value") or 0)
                    if eligible
                    else None,
                    "text_preview": witness.get("text_preview"),
                    "non_gating": True,
                    "research_only": True,
                    "writes_canon": False,
                }
            )

    return {
        "schema": "shadow_line_witness_registry_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "track_wall": {
            "logos_core_mutation_forbidden": True,
            "merge_into_canon_31k_41k": False,
            "track_a_bridge": False,
        },
        "summary": {
            "registry_rows": len(rows),
            "numeric_comparison_eligible_rows": numeric_eligible,
            "entry_ids": sorted({r.get("entry_id") for r in rows if r.get("entry_id")}),
        },
        "rows": rows,
        "reproduce": "py scripts/build_shadow_line_witness_registry_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sm = doc["summary"]
    ok = int(sm.get("registry_rows") or 0) >= 8 and int(sm.get("numeric_comparison_eligible_rows") or 0) >= 4
    print(json.dumps({"ok": ok, "summary": sm, "out": str(args.out.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
