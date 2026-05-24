#!/usr/bin/env python3
"""Refresh COMP-ATOM research manifest (paths only, no active report write)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    entries = [
        ("COMP-ATOM-01 control", "comp_atom01_control_v1.json", "bridge OFF isolated eval"),
        ("COMP-ATOM-01 bridge ON", "comp_atom01_bridge_on_v1.json", "bridge ON isolated eval"),
        ("COMP-ATOM-01 AB summary", "comp_atom01_ab_summary_v1.json", "Δ saving/Jaccard"),
        ("COMP-ATOM-02 lexicon hits", "comp_atom02_lexicon_must_keep_analysis_v1.json", "41k must_keep ablation"),
        ("COMP-ATOM-02 sentence pointer", "comp_atom02_genesis_pointer_sentence_poc_v1.json", "40 sentences 0/40 ok"),
        ("COMP-ATOM-02 ko tokenizer", "comp_atom02_ko_pointer_tokenizer_poc_v1.json", "tokenizer strategy compare"),
        ("COMP-ATOM-02 vocab coverage", "comp_atom02_bench_genesis_vocab_coverage_v1.json", "518 bench tokens vs genesis 64"),
        ("COMP-ATOM-02 expanded codebook", "comp_atom02_expanded_lexicon_codebook_poc_v1.json", "70 terms bench∩41k still 0/40 ok"),
        ("COMP-ATOM-02 pointer feasibility", "comp_atom02_pointer_feasibility_summary_v1.json", "closed-dict vs Track A one-pager"),
        ("COMP-ATOM B-track closure", "comp_atom_track_b_closure_v1.json", "01-04 status + frozen active"),
        ("NotebookLM source pack", "comp_atom_notebooklm_source_pack_v1.json", "7 paths for manual add_source"),
        ("COMP-ATOM research manifest", "comp_atom_research_manifest_v1.json", "path index"),
        ("COMP-ATOM-02 join summary", "comp_atom02_join_poc_summary_v1.json", "index of PoCs"),
        ("COMP-ATOM-04 promotion dryrun", "comp_atom04_promotion_dryrun_v1.json", "human gate; active unchanged"),
        ("Frozen active (read-only)", "../docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json", "47.5% GO SSOT"),
        ("Genesis chain failure", "genesis_pointer_chain_failure_note_v1.json", "B-track HOLD expected"),
    ]
    manifest = {
        "schema": "comp_atom_research_manifest_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "active_report_write_forbidden": True,
        "artifacts": [
            {
                "label": label,
                "path": f"reports/constitution/btrack_pilot/{fname}" if not fname.startswith("../") else fname.replace("../", ""),
                "note": note,
                "exists": (PILOT / fname if not fname.startswith("../") else ROOT / fname.replace("../", "")).is_file(),
            }
            for label, fname, note in entries
        ],
    }
    path = PILOT / "comp_atom_research_manifest_v1.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(path), "exists": sum(1 for a in manifest["artifacts"] if a["exists"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
