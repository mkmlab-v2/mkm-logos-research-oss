#!/usr/bin/env python3
"""COMP-ATOM B-track closure card (research complete, active frozen)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    active = json.loads(ACTIVE.read_text(encoding="utf-8")) if ACTIVE.is_file() else {}
    cm = active.get("compression_metrics") or {}
    feas = {}
    fp = PILOT / "comp_atom02_pointer_feasibility_summary_v1.json"
    if fp.is_file():
        feas = json.loads(fp.read_text(encoding="utf-8"))

    out = {
        "schema": "comp_atom_track_b_closure_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_frozen": {
            "path": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
            "global_token_saving_rate": cm.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
            "apply_gematria_4d_bridge_policy": (active.get("active_profile") or {}).get(
                "apply_gematria_4d_bridge_policy"
            ),
        },
        "missions": {
            "COMP-ATOM-01": {"status": "done", "artifact": "comp_atom01_ab_summary_v1.json"},
            "COMP-ATOM-02": {"status": "done", "artifact": "comp_atom02_pointer_feasibility_summary_v1.json"},
            "COMP-ATOM-03": {"status": "done", "artifact": "reports/ms_rq019_paste_ready/technical_moat_sector_paste.txt"},
            "COMP-ATOM-04": {
                "status": "done"
                if (ROOT / "docs/final/artifacts/multilens_ultra_compression_track_a_promotion_signoff_v1_latest.json").is_file()
                else "blocked_human",
                "artifact": "multilens_ultra_compression_track_a_promotion_signoff_v1_latest.json",
            },
            "COMP-ANCHOR-05": {
                "status": "done"
                if (PILOT / "comp_anchor05_verse_pool_full_scan_v1.json").is_file()
                else "pending",
                "artifact": "comp_anchor05_verse_pool_full_scan_v1.json",
            },
            "COMP-ANCHOR-06": {
                "status": "done"
                if (PILOT / "comp_anchor06_top_verse_pools_v1.json").is_file()
                and (PILOT / "comp_anchor06_registry_codebook_bridge_v1.json").is_file()
                else "pending",
                "artifact": "comp_anchor06_top_verse_pools_v1.json",
            },
            "COMP-ANCHOR-07": {
                "status": "done"
                if (PILOT / "comp_anchor07_registry_seed_mapping_poc_v1.json").is_file()
                else "pending",
                "artifact": "comp_anchor07_registry_seed_mapping_poc_v1.json",
            },
            "COMP-ANCHOR-08": {
                "status": "done"
                if (PILOT / "comp_anchor08_seed_curation_queue_v1.json").is_file()
                else "pending",
                "artifact": "comp_anchor08_seed_curation_queue_v1.json",
            },
            "COMP-ATOM-05-detail": {
                "status": "done"
                if (PILOT / "comp_atom05_bridge_boost_detail_v1.json").is_file()
                else "pending",
                "artifact": "comp_atom05_bridge_boost_detail_v1.json",
            },
        },
        "pointer_verdict": feas.get("verdict"),
        "manifest": "comp_atom_research_manifest_v1.json",
        "forbidden_without_human": [
            "overwrite MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json without backup",
            "apply_gematria_4d_bridge_policy true on active without AB + human",
        ],
        "recommended_next_non_track_a": [
            "NotebookLM B-track: manual IJEOMA_BTRACK pack (no MCP)",
            "comp_anchor05 verse pool full scan",
            "comp_atom02_pointer_research_brief_v1.json",
        ],
    }
    path = PILOT / "comp_atom_track_b_closure_v1.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(path), "saving": out["track_a_active_frozen"].get("global_token_saving_rate")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
