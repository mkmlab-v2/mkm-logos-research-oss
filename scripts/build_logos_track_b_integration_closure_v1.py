#!/usr/bin/env python3
"""Track B integration closure — phases F–H metrics in one audit JSON."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/logos_track_b_integration_closure_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _citation_lock_ok(theme_id: str) -> bool:
    path = ROOT / f"docs/final/artifacts/logos_deep_research_distill_{theme_id}_citation_lock_latest.json"
    doc = _load(path)
    if not doc:
        return False
    lock = doc.get("citation_lock") or {}
    locked_count = int(lock.get("locked_count") or 0)
    evidence_n = len(doc.get("evidence_refs") or [])
    return locked_count >= 3 and locked_count >= max(1, evidence_n)


def _preset_theme_ids() -> list[str]:
    presets = _load(ROOT / "docs/final/artifacts/LOGOS_TRACK_B_THEME_PRESETS_V1.json") or {}
    return list((presets.get("themes") or {}).keys())


def build() -> dict[str, Any]:
    phase_f = _load(ROOT / "reports/logos_b2b_phase_f_v1_latest.json")
    phase_h = _load(ROOT / "reports/logos_track_b_phase_h_v1_latest.json")
    phase_l = _load(ROOT / "reports/logos_track_b_phase_l_v1_latest.json")
    phase_o = _load(ROOT / "reports/logos_track_b_phase_o_v1_latest.json")
    graphrag = _load(ROOT / "reports/logos_themed_graphrag_seed_retrieval_v1_latest.json")
    topic_graphrag = _load(ROOT / "reports/logos_topic_graphrag_seed_retrieval_v1_latest.json")
    dual = _load(ROOT / "reports/logos_themed_retrieval_dual_backend_v1_latest.json")
    verifier = _load(ROOT / "reports/logos_b2b_proposal_goal_verifier_v1_latest.json")
    master = _load(ROOT / "docs/final/artifacts/logos_b2b_proposal_master_summary_v1_latest.json")
    registry = _load(ROOT / "docs/final/artifacts/logos_reasoning_pattern_registry_v1_latest.json")
    p5_gate = _load(ROOT / "docs/final/artifacts/p5_manuscript_integrity_gate_v1_latest.json")
    post_gate = _load(ROOT / "docs/final/artifacts/entry_13_post_promotion_gate_v1_latest.json")
    p8_gate = _load(ROOT / "docs/final/artifacts/logos_bible_rail_completion_gate_v1_latest.json")
    reg4 = _load(ROOT / "reports/shadow_4q_ps5_witness_registry_v1_latest.json")
    map_4q = _load(ROOT / "reports/dss_4q_ps5_line_witness_map_v1_latest.json")

    gr_sm = (graphrag or {}).get("summary") or {}
    topic_sm = (topic_graphrag or {}).get("summary") or {}
    theme_ids = _preset_theme_ids()
    citation_valid_count = sum(1 for tid in theme_ids if _citation_lock_ok(tid))
    llm_dan = _citation_lock_ok("dan_aramaic")
    llm_john = _citation_lock_ok("john_1_logos")
    gates = {
        "b2b_verifier_ok": (verifier or {}).get("ok") is True,
        "master_summary_promoted": (master or {}).get("promoted") is True,
        "phase_f_ok": (phase_f or {}).get("ok") is True,
        "phase_h_ok": (phase_h or {}).get("ok") is True,
        "phase_l_ok": (phase_l or {}).get("ok") is True,
        "phase_o_ok": (phase_o or {}).get("ok") is True,
        "graphrag_organic_42_42": gr_sm.get("seed_hits_organic") == "42/42",
        "citation_valid_themes_12": citation_valid_count >= max(10, len(theme_ids) - 2),
        "llm_citation_valid_dan": llm_dan,
        "llm_citation_valid_john": llm_john,
        "p5_manuscript_integrity_ok": (p5_gate or {}).get("gate_ok") is True,
        "entry_13_post_promotion_ok": (post_gate or {}).get("gate_ok") is True,
        "bible_rail_completion_ok": (p8_gate or {}).get("gate_ok") is True,
        "track_a_bridge": False,
        "live_trading_bridge": False,
    }
    positive_gates = (
        gates["b2b_verifier_ok"],
        gates["master_summary_promoted"],
        gates["phase_f_ok"],
        gates["phase_h_ok"],
        gates["phase_l_ok"],
        gates["graphrag_organic_42_42"],
        gates["citation_valid_themes_12"],
    )
    all_ok = all(positive_gates)

    return {
        "schema": "logos_track_b_integration_closure_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "gates": gates,
        "ok": all_ok,
        "metrics": {
            "graphrag_seed_organic": gr_sm.get("seed_hits_organic"),
            "graphrag_seed_full": gr_sm.get("seed_hits_full"),
            "topic_graphrag_seed_hits": topic_sm.get("seed_hits"),
            "topic_graphrag_topic_hits": topic_sm.get("topic_hits"),
            "dual_backend_themes": len((dual or {}).get("themes") or []),
            "reasoning_patterns": len((registry or {}).get("patterns") or []),
            "b2b_promoted_claims": (master or {}).get("promoted_claim_count")
            or len((master or {}).get("promoted_claims") or []),
            "phase_o_ledger_records": (phase_o or {}).get("ledger_records"),
            "phase_o_path_gate_pass": (phase_o or {}).get("path_verification_gate_pass"),
            "llm_citation_valid_themes": f"{citation_valid_count}/{len(theme_ids)}",
            "p5_manuscript_integrity_gate_ok": (p5_gate or {}).get("gate_ok"),
            "entry_13_4q_provisional_rows": (map_4q or {}).get("summary", {}).get("provisional_lexical_anchor_rows"),
            "entry_13_commander_verified_rows": (reg4 or {}).get("summary", {}).get("commander_verified_rows"),
            "entry_13_shadow_verse_anchor": (reg4 or {}).get("shadow_verse_anchor"),
            "bible_rail_status": (p8_gate or {}).get("bible_rail_status"),
        },
        "artifacts": {
            "digest": "reports/logos_track_b_commander_dual_theme_digest_latest.md",
            "entry_13_post_promotion_report": "reports/entry_13_post_promotion_commander_report_v1_latest.md",
            "bible_rail_completion_report": "reports/logos_bible_rail_completion_commander_report_v1_latest.md",
            "manuscript_integrity_audit": "reports/manuscript_integrity_audit_11q5_psalms_commander_v1_latest.md",
            "operator_board": "reports/dss_line_witness_verification_operator_board_v1_latest.md",
            "ms_appendix": "reports/external_validation_ms_evidence_pack_v1_latest/ms_b2b_logos_logic_verifier_appendix_v1.md",
            "reasoning_registry": "docs/final/artifacts/logos_reasoning_pattern_registry_v1_latest.json",
            "themed_registry": "docs/final/artifacts/logos_concept_bridge_registry_themed_v1_latest.json",
        },
        "reproduce": "py scripts/build_logos_track_b_integration_closure_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "gates": doc["gates"], "out": str(args.out.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
