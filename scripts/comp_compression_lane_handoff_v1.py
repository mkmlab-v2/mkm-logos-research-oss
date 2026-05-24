#!/usr/bin/env python3
"""Unified COMP+B-track lane handoff JSON (cross-chat merge, no active writes)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
OUT = PILOT / "comp_compression_lane_handoff_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(name: str) -> dict[str, Any]:
    p = PILOT / name
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def _matrix_summary(doc: dict[str, Any]) -> dict[str, Any]:
    benches: dict[str, Any] = {}
    for m in doc.get("matrices") or []:
        if not isinstance(m, dict):
            continue
        label = str(m.get("bench_label") or "bench")
        cells: dict[str, Any] = {}
        for c in m.get("cells") or []:
            if not isinstance(c, dict):
                continue
            cid = str(c.get("cell_id") or "")
            met = c.get("metrics") or {}
            if not cid or not isinstance(met, dict):
                continue
            cells[cid] = {
                "global_token_saving_rate": met.get("global_token_saving_rate"),
                "avg_reconstruction_fidelity_jaccard": met.get(
                    "avg_reconstruction_fidelity_jaccard"
                ),
                "graph_wire_selective_bridge": c.get("graph_wire_selective_bridge"),
            }
        benches[label] = {
            "bridge_boost_cases": m.get("bridge_boost_cases"),
            "cells": cells,
        }
    return {
        "artifact": "comp_atom05_profile_matrix_sweep_v1.json",
        "generated_at_utc": doc.get("generated_at_utc"),
        "active_report_untouched": doc.get("active_report_untouched"),
        "benches": benches,
    }


def _pointer_summary(doc: dict[str, Any]) -> dict[str, Any]:
    t2 = doc.get("t2_refresh") or {}
    return {
        "artifact": "comp_atom02_pointer_feasibility_summary_v1.json",
        "verdict": doc.get("verdict"),
        "strict_full_sentence_ok_40": t2.get("strict_full_sentence_ok_40"),
        "cases_partial_coverage": t2.get("cases_partial_coverage"),
        "track_a_mechanism": (doc.get("track_a_frozen") or {}).get("mechanism"),
    }


def _anchor_lane_summary() -> dict[str, Any]:
    scan = _load("comp_anchor05_verse_pool_full_scan_v1.json")
    bridge = _load("comp_anchor06_registry_codebook_bridge_v1.json")
    top = _load("comp_anchor06_top_verse_pools_v1.json")
    reg_rows = bridge.get("bridge_rows") or []
    unmapped = sum(
        1 for r in reg_rows if isinstance(r, dict) and r.get("bridge_status") == "unmapped"
    )
    return {
        "scan_artifact": "comp_anchor05_verse_pool_full_scan_v1.json",
        "verses_scanned": (scan.get("summary") or {}).get("verses_scanned"),
        "registry_conceptual_hit_zero": [
            r.get("atom_id")
            for r in (scan.get("registry_atoms") or [])
            if isinstance(r, dict) and (r.get("verses_with_hits") or 0) == 0
        ],
        "top_pools_artifact": "comp_anchor06_top_verse_pools_v1.json",
        "top_pool_atom_ids": [
            p.get("atom_id") for p in (top.get("pools") or [])[:8] if isinstance(p, dict)
        ],
        "registry_bridge_unmapped_count": unmapped,
        "wire_candidates_artifact": "comp_anchor07_wire_atom_candidates_v1.json",
    }


def _atom05_lane_summary() -> dict[str, Any]:
    compare = _load("comp_atom05_compare_prior_v1.json")
    matrix = _load("comp_atom05_profile_matrix_sweep_v1.json")
    return {
        "compare_prior_artifact": "comp_atom05_compare_prior_v1.json",
        "headline": compare.get("headline"),
        "track_a_frozen_headline": compare.get("track_a_frozen_headline"),
        "profile_matrix": _matrix_summary(matrix),
        "fact_lock_bundle_step": "5c4 pytest (SkipCompAtom05WireSmoke)",
        "parallel_bundle_artifact": "comp_atom05_parallel_bundle_v1.json",
        "stub_bench_align": "profile_evaluate_report_kwargs_v2",
    }


def main() -> int:
    active = json.loads(ACTIVE.read_text(encoding="utf-8")) if ACTIVE.is_file() else {}
    cm = active.get("compression_metrics") or {}
    handoff = {
        "schema": "comp_compression_lane_handoff_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "[HYPO]",
        "track_wall": {
            "a_track_auto_promotion": False,
            "live_trading_trigger": False,
            "active_report_write": False,
        },
        "track_a_frozen": {
            "global_token_saving_rate": cm.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": cm.get(
                "avg_reconstruction_fidelity_jaccard"
            ),
            "apply_gematria_4d_bridge_policy": (active.get("active_profile") or {}).get(
                "apply_gematria_4d_bridge_policy"
            ),
            "artifact": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
        },
        "cross_chat_sync": {
            "mission_log": "MISSION_LOG.md",
            "rule": "Do not merge chat transcripts; sync via this JSON + MISSION_LOG sections only.",
            "forbidden_fusion": [
                "31k verse scan -> economy must_keep or Track A zone",
                "BOUNDARY_COMMAND registry -> master codebook auto-merge",
                "Claim single-request API equals 40-case bench 47.1%/0.897 without per-text bridge_boost",
                "GraphRAG must_keep anchors as primary KPI lever (measured delta 0 on full bench)",
            ],
            "integration_team_ssot": (
                "reports/constitution/btrack_pilot/comp_atom05_profile_matrix_brief_v1.json"
            ),
            "profile_presets": (_load("comp_atom05_profile_matrix_brief_v1.json").get("profile_presets")),
            "do_not_promote": (_load("comp_atom05_profile_matrix_brief_v1.json").get("do_not_promote")),
            "v2_draft_contract": (_load("comp_atom05_profile_matrix_brief_v1.json").get("v2_draft_contract")),
            "recommended_v2_payload_b_track": (
                (_load("comp_atom05_profile_matrix_brief_v1.json").get("profile_presets") or {}).get(
                    "btrack_recommended_v2"
                )
                or {
                    "compression_profile": "economy",
                    "emit_semantic_pointer": True,
                    "graph_wire_selective_bridge": True,
                }
            ),
            "v2_staging_promotion_scope": (
                "reports/constitution/btrack_pilot/comp_v2_wire_staging_promotion_scope_v1.json"
            ),
            "v2_staging_phase1": "commander scope v2_wire_opt_in — wire opt-in staging only; active untouched",
            "track_a_frozen_preset": (
                (_load("comp_atom05_profile_matrix_brief_v1.json").get("profile_presets") or {}).get(
                    "track_a_frozen"
                )
            ),
            "stub_bench_align": "profile_evaluate_report_kwargs_v2 (economy+wire -> _base_eval_kwargs)",
            "anchor07_wire_ab_artifact": "comp_anchor07_wire_source_ab_v1.json",
            "wire_atom_env": "MKM_WIRE_ATOM_IDS_SOURCE=poc|anchor07|merged (default poc)",
            "optional_next": [],
        },
        "lanes": {
            "comp_atom_closure": _load("comp_atom_track_b_closure_v1.json").get("missions"),
            "comp_atom05": _atom05_lane_summary(),
            "anchor_corpus": _anchor_lane_summary(),
            "pointer": _pointer_summary(_load("comp_atom02_pointer_feasibility_summary_v1.json")),
            "ijeoma_b7": _load("comp_ijeoma_b7_manifest_closure_v1.json"),
        },
        "notebooklm_manual": {
            "compression_pack": "reports/notebooklm_lens_packs_v1/COMPRESSION_BTRACK/",
            "ijeoma_pack": "reports/notebooklm_lens_packs_v1/IJEOMA_BTRACK/",
            "auto_script": "scripts/push_comp_btrack_nl_mcp_v1.py",
            "commander_auto_upload_approved": True,
        },
        "excluded_this_lane": ["MS-PASTE", "HWPX"],
    }
    OUT.write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
