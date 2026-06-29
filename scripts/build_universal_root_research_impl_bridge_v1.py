#!/usr/bin/env python3
"""Build research Tier0→1 ↔ Phase 11 implementation bridge artifact [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/universal_root_research_impl_bridge_v1_latest.json"

TIER0_PROMPT = ROOT / "docs/research/raw/universal_root_lexicon_matrix_gemini_prompt_v1.md"
TIER0_REPORT = ROOT / "docs/research/raw/universal_root_lexicon_matrix_gemini_report_2026-06-21.md"
TIER0_SWEEP = ROOT / "docs/research/raw/universal_root_lexicon_matrix_cursor_sweep_2026-06-21.md"
MERGED_LIT = ROOT / "docs/research/UNIVERSAL_ROOT_LEXICON_MATRIX_MERGED_LIT_REVIEW_2026-06-21.md"
CITATION_LOCK = ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_LEXICON_MATRIX_LIT_REVIEW_2026-06-21_citation_lock_latest.json"
GATE_SPEC = ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_GATE_SPEC_V1.json"
GATE_EVAL = ROOT / "reports/universal_root_gate_eval_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rel(path: Path) -> str | None:
    if not path.is_file():
        return None
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _snapshot(path: Path) -> dict[str, Any]:
    return {"path": _rel(path), "exists": path.is_file()}


def build_bridge(*, gate_chain_doc: dict[str, Any] | None = None) -> dict[str, Any]:
    gate_spec = _read_json(GATE_SPEC)
    gate_eval = _read_json(GATE_EVAL)
    citation = _read_json(CITATION_LOCK)
    baseline = gate_spec.get("baseline_observed") if isinstance(gate_spec.get("baseline_observed"), dict) else {}
    eval_summary = gate_eval.get("evaluation") if isinstance(gate_eval.get("evaluation"), dict) else {}
    shadow = baseline.get("distortion_shadow_remapped") if isinstance(baseline.get("distortion_shadow_remapped"), dict) else {}
    route_stress = baseline.get("route_stress_live_32") if isinstance(baseline.get("route_stress_live_32"), dict) else {}

    tier_files = {
        "tier0_prompt": _snapshot(TIER0_PROMPT),
        "tier0_gemini_report": _snapshot(TIER0_REPORT),
        "tier0_cursor_sweep": _snapshot(TIER0_SWEEP),
        "merged_lit_review": _snapshot(MERGED_LIT),
        "citation_lock": _snapshot(CITATION_LOCK),
    }
    tier_ok = all(v.get("exists") for v in tier_files.values())

    impl_pointers = {
        "gate_spec": _rel(GATE_SPEC),
        "gate_eval": _rel(GATE_EVAL),
        "phase11e_chain": "reports/logos_graphrag_phase11e_nsm_crosswalk_repair_chain_v1_latest.json",
        "phase11i_chain": "reports/logos_graphrag_phase11i_shallow_modelfile_tune_chain_v1_latest.json",
        "phase11k_chain": "reports/logos_graphrag_phase11k_sidecar_ablation_v3_chain_v1_latest.json",
        "phase11l_chain": "reports/logos_graphrag_phase11l_closure_refresh_chain_v1_latest.json",
        "phase11n_chain": "reports/logos_graphrag_phase11n_fact_support_gate_chain_v1_latest.json",
        "phase11o_chain": "reports/logos_graphrag_phase11o_nl_sandbox_sync_chain_v1_latest.json",
        "sidecar_ablation_v3": "reports/universal_root_sidecar_ablation_v3_latest.json",
        "mdl_prune_poc": "reports/universal_root_mdl_prune_poc_v1_latest.json",
    }

    fact_doc = (gate_chain_doc or {}).get("fact_support") if isinstance(gate_chain_doc, dict) else {}
    if not isinstance(fact_doc, dict):
        fact_doc = {}
    fact_gate_ok = fact_doc.get("gate_ok")
    if fact_gate_ok is None:
        fact_gate_ok = fact_doc.get("ok")

    bridge_ok = (
        tier_ok
        and bool(citation.get("gate_ok"))
        and bool(eval_summary.get("all_enabled_planes_ok"))
        and baseline.get("phase") is not None
    )
    if gate_chain_doc:
        bridge_ok = bridge_ok and bool(fact_gate_ok)

    return {
        "schema": "universal_root_research_impl_bridge_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_promotion_forbidden": True,
        "bridge_ok": bridge_ok,
        "tier0_tier1_files": tier_files,
        "citation_lock_pass_rate": citation.get("citation_pass_rate"),
        "fact_support_pass_rate": fact_doc.get("support_pass_rate"),
        "fact_support_gate_ok": fact_gate_ok,
        "merged_lit_review_gate_chain": gate_chain_doc or {},
        "implementation_snapshot": {
            "gate_spec_phase": baseline.get("phase"),
            "research_ready_decision": eval_summary.get("research_ready_decision"),
            "all_enabled_planes_ok": eval_summary.get("all_enabled_planes_ok"),
            "shadow_distortion_rate": shadow.get("english_only_distortion_rate"),
            "shadow_gate_ok": shadow.get("gate_ok"),
            "shallow_stress_router_hit_rate": route_stress.get("router_hit_rate"),
            "shallow_stress_routing_oracle_gap": route_stress.get("routing_oracle_gap"),
            "modelfile_version": route_stress.get("modelfile_version"),
        },
        "implementation_pointers": impl_pointers,
        "reproduce": "py scripts/run_logos_graphrag_phase11o_nl_sandbox_sync_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate-chain-json", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    gate_chain_doc = None
    if args.gate_chain_json and args.gate_chain_json.is_file():
        gate_chain_doc = _read_json(args.gate_chain_json)

    doc = build_bridge(gate_chain_doc=gate_chain_doc)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "bridge_ok": doc["bridge_ok"], "out": str(args.out)}, ensure_ascii=False))
    if args.strict and not doc["bridge_ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
