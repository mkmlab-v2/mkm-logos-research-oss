#!/usr/bin/env python3
"""Bench lexicon SSOT pointer: production 41658, optional 3a overlay (research), archived 41775."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
OUT = PILOT / "master_codebook_bench_lexicon_pointer_v1_latest.json"
P658 = PILOT / "master_codebook_lexicon_v1_41658_rows_latest.json"
P775 = PILOT / "master_codebook_lexicon_v1_41775_rows_archived_20260523.json"
P3A = PILOT / "master_codebook_lexicon_v1_41658_3a_pilot_overlay.json"
PILOT_3A = PILOT / "master_codebook_3a_overlay_pilot_v1.json"
HOLD_3B = PILOT / "master_codebook_3b_hold_verdict_v1_latest.json"
FEAS = PILOT / "master_codebook_other_align_feasibility_v1.json"
HEADLINE = ROOT / "reports/compression_track_a_headline_policy_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def _row_count(path: Path) -> int | None:
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    rc = doc.get("row_count")
    if isinstance(rc, int):
        return rc
    entries = doc.get("entries")
    if isinstance(entries, list):
        return len(entries)
    return None


def main() -> int:
    pilot_3a: dict[str, Any] | None = None
    if PILOT_3A.is_file():
        pilot_3a = json.loads(PILOT_3A.read_text(encoding="utf-8"))

    doc: dict[str, Any] = {
        "schema": "master_codebook_bench_lexicon_pointer_v1",
        "generated_at_utc": _utc(),
        "production_ssot": {
            "role": "Track A bench · MS Policy A · PROFILE_BENCH_SSOT economy",
            "path": _rel(P658),
            "row_count": _row_count(P658),
            "golden40_kpi": {
                "global_token_saving_rate": 0.49085794655414905,
                "avg_reconstruction_fidelity_jaccard": 0.8727418293565741,
                "case_count": 40,
            },
            "ms_paste_headline": "49.1% / Jaccard 0.873 (rounded)",
        },
        "research_overlay_3a": {
            "role": "B-track pilot only — restores frozen 41775 KPI on Golden 40; not ACTIVE",
            "path": _rel(P3A) if P3A.is_file() else None,
            "row_count": _row_count(P3A) if P3A.is_file() else None,
            "pilot_report": _rel(PILOT_3A) if PILOT_3A.is_file() else None,
            "verdict": (pilot_3a or {}).get("verdict"),
            "golden40_kpi": (pilot_3a or {}).get("metrics_41658_3a_overlay"),
            "atom_ids_added_count": ((pilot_3a or {}).get("overlay_meta") or {}).get("atom_ids_added_count"),
            "promotion": "HOLD — human sign-off before ACTIVE or MS body merge",
        },
        "archived_41775": {
            "role": "A/B diff reference only",
            "path": _rel(P775) if P775.is_file() else None,
            "row_count": _row_count(P775) if P775.is_file() else None,
            "frozen_headline_kpi": {
                "global_token_saving_rate": 0.47538677918424754,
                "avg_reconstruction_fidelity_jaccard": 0.8904921794966301,
            },
        },
        "frozen_ms_external_headline": {
            "global_token_saving_rate_pct": 47.54,
            "avg_reconstruction_fidelity_jaccard": 0.8904921794966301,
            "note": "MS paste / CENTRAL external copy until commander reopens MS lane",
        },
        "pointers": {
            "headline_policy": _rel(HEADLINE) if HEADLINE.is_file() else None,
            "other_align_feasibility": _rel(FEAS) if FEAS.is_file() else None,
            "golden40_ab": _rel(PILOT / "master_codebook_golden40_lexicon_ab_v1.json"),
            "reexport_3c_scope": _rel(PILOT / "master_codebook_3c_reexport_scope_v1_latest.json"),
            "hold_3b_verdict": _rel(HOLD_3B) if HOLD_3B.is_file() else None,
            "expansion_dryrun_3a_lexicon": _rel(
                ROOT / "reports/golden_40_expansion_dryrun_3a_lexicon_v1_latest.json"
            ),
            "expansion_lexicon_ab_compare": _rel(
                ROOT / "reports/golden_40_expansion_lexicon_ab_compare_v1_latest.json"
            ),
            "expansion_pool_compare": _rel(ROOT / "reports/golden_40_expansion_pool_compare_v1_latest.json"),
            "ancient_corpus_bridge_research": _rel(
                ROOT / "docs/research/ANCIENT_CORPUS_COMPRESSION_SRE_BRIDGE_V1.md"
            ),
            "ancient_corpus_bridge_pointer": _rel(
                ROOT / "docs/final/artifacts/ancient_corpus_compression_sre_bridge_pointer_v1_latest.json"
            ),
            "polar_coord_compression_hypo": _rel(ROOT / "reports/polar_coord_compression_hypo_v1_latest.json"),
            "cooc_cartesian_routing_poc_v2": _rel(
                ROOT / "reports/other_cooc_cartesian_routing_poc_v2_latest.json"
            ),
            "golden40_per_lane_report": _rel(ROOT / "reports/golden40_expansion_per_lane_report_v1_latest.json"),
            "rq021_commander_btrack_signoff": _rel(
                ROOT / "docs/final/artifacts/rq021_commander_btrack_signoff_v1_latest.json"
            ),
            "rq021_post_signoff_bundle": _rel(ROOT / "reports/rq021_post_signoff_bundle_v1_latest.json"),
        },
        "ms_narrative_when_resumed": {
            "status": "HOLD",
            "research_only": True,
            "one_liner_ko": "41k greek/hebrew lexicon aligns with epigraphy/paleography digital restoration narrative (Ithaca/Enoch/SQE references only).",
            "kpi_for_slides": "Policy A 49.1% / Jaccard 0.873 — not 47.5%/0.890 or external CER",
            "bridge_doc": _rel(ROOT / "docs/research/ANCIENT_CORPUS_COMPRESSION_SRE_BRIDGE_V1.md"),
        },
        "fail_comp_004": "Do not overwrite MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json from this artifact.",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
