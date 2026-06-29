#!/usr/bin/env python3
"""Sync Fact-Lock metrics for logos.jema-ai.com product landing [HYPO / research_only]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_REPORTS = ROOT / "reports/logos_research_product_metrics_v1_latest.json"
OUT_NO1KMEDI = ROOT / "projects/no1kmedi/public/data/logos_research_product_metrics_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def build() -> dict[str, Any]:
    phase_o = _load(ROOT / "reports/logos_track_b_phase_o_v1_latest.json")
    phase_n = _load(ROOT / "reports/logos_track_b_phase_n_v1_latest.json")
    closure = _load(ROOT / "reports/logos_track_b_integration_closure_v1_latest.json")
    bridge = _load(ROOT / "reports/logos_cross_theme_invariant_bridge_v1_latest.json")
    path_gate = _load(ROOT / "reports/logos_path_verification_gate_v1_latest.json")
    mapping = _load(ROOT / "reports/logos_b2b_logic_mapping_audit_v1_latest.json")
    lexicon_audit = _load(ROOT / "reports/logos_41k_4d_reclassification_audit_v1_latest.json")
    key_shadow = _load(ROOT / "reports/verse_metadata_shadow_v1_latest.json")
    optimization = _load(ROOT / "reports/optimization_impact_v1_latest.json")
    optimization_preset = _load(ROOT / "reports/optimization_impact_preset_v1_latest.json")
    preset = _load(ROOT / "reports/tracka_shadow_default_preset_v1_latest.json")
    postit_q = _load(ROOT / "reports/shadow_postits_quality_gate_v1_latest.json")
    anchor_index = _load(ROOT / "reports/logos_bidirectional_anchor_index_v1_latest.json")
    sweep = _load(ROOT / "reports/tracka_shadow_sweep_v1_latest.json")

    metrics = (closure or {}).get("metrics") or {}
    pg = (path_gate or {}).get("summary") or {}
    br = (bridge or {}).get("summary") or {}
    cov = (lexicon_audit or {}).get("phase_pb_lexicon_coverage") or {}
    shadow = (lexicon_audit or {}).get("phase_pc_path_four_d_shadow") or {}
    key_summary = (key_shadow or {}).get("summary") or {}
    opt_delta = (optimization_preset or optimization or {}).get("delta_shadow_minus_raw") or {}
    qsum = (postit_q or {}).get("summary") or {}
    asum = (anchor_index or {}).get("summary") or {}

    return {
        "schema": "logos_research_product_metrics_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "public_domain": "logos.jema-ai.com",
        "metrics": {
            "graphrag_seed_organic": metrics.get("graphrag_seed_organic"),
            "llm_citation_valid_themes": metrics.get("llm_citation_valid_themes"),
            "shared_hubs": br.get("shared_hub_count"),
            "insight_total_units": (phase_n or {}).get("insight_total_units"),
            "ledger_records": (phase_o or {}).get("ledger_records"),
            "path_verification_pass_rate": pg.get("pass_rate"),
            "path_verification_gate_pass": pg.get("gate_pass"),
            "b2b_structure_map_verdict": (mapping.get("summary") or {}).get("verdict"),
            "phase_o_ok": (phase_o or {}).get("ok"),
            "integration_closure_ok": (closure or {}).get("ok"),
            "lexicon_4d_coverage_rate_shadow": cov.get("lexicon_4d_coverage_rate"),
            "four_d_coherence_mean_shadow": shadow.get("mean_four_d_coherence"),
            "four_d_human_review_hint_count_shadow": shadow.get("human_review_hint_count"),
            "key_verse_shadow_rows": key_summary.get("shadow_rows"),
            "tracka_shadow_delta_token_saving_rate": opt_delta.get("global_token_saving_rate"),
            "tracka_shadow_delta_jaccard": opt_delta.get("avg_reconstruction_fidelity_jaccard"),
            "tracka_shadow_delta_sensitive_integrity": opt_delta.get("avg_sensitive_integrity"),
            "shadow_postit_quality_ok": qsum.get("overall_ok"),
            "anchor_index_verse_nodes": asum.get("verse_nodes"),
            "anchor_index_atom_nodes": asum.get("atom_nodes"),
            "tracka_shadow_sweep_pareto_count": len((sweep or {}).get("pareto_top5") or []),
            "tracka_shadow_preset_terms": preset.get("selected_terms_count"),
            "tracka_shadow_preset_threshold": (preset.get("primary_config") or {}).get("threshold"),
            "tracka_shadow_preset_term_cap": (preset.get("primary_config") or {}).get("term_cap"),
        },
        "artifact_paths": {
            "phase_o": "reports/logos_track_b_phase_o_v1_latest.json",
            "phase_n": "reports/logos_track_b_phase_n_v1_latest.json",
            "digest": "reports/logos_phase_o_digest_v1_latest.md",
        },
        "reproduce": "py scripts/build_logos_research_product_metrics_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_REPORTS)
    ap.add_argument("--no1kmedi", type=Path, default=OUT_NO1KMEDI)
    args = ap.parse_args()

    doc = build()
    for path in (args.out, args.no1kmedi):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok = bool(doc["metrics"].get("phase_o_ok")) or bool(doc["metrics"].get("integration_closure_ok"))
    print(json.dumps({"ok": ok, "out": str(args.out), "no1kmedi": str(args.no1kmedi)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
