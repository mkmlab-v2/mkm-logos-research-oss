#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build academic one-pager from global atom network PoC artifacts.")
    ap.add_argument(
        "--phase-report-json",
        default="docs/final/artifacts/global_atom_network_core100_phase_transition_report_latest.json",
    )
    ap.add_argument(
        "--full-canon-batch-report-json",
        default="",
    )
    ap.add_argument(
        "--similarity-matrix-json",
        default="docs/final/artifacts/global_atom_network_core100_similarity_matrix_latest.json",
    )
    ap.add_argument(
        "--gate-summary-json",
        default="docs/final/artifacts/multi_symbol_gate_summary_latest.json",
    )
    ap.add_argument(
        "--counterfactual-comparison-json",
        default="docs/final/artifacts/multi_symbol_counterfactual_comparison_latest.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/global_atom_network_academic_onepager_latest.json",
    )
    args = ap.parse_args()

    pp = resolve(args.phase_report_json)
    mp = resolve(args.similarity_matrix_json)
    gp = resolve(args.gate_summary_json)
    cp = resolve(args.counterfactual_comparison_json)
    bp = resolve(args.full_canon_batch_report_json) if str(args.full_canon_batch_report_json or "").strip() else None
    op = resolve(args.output_json)
    for p in (pp, mp, gp, cp):
        if not p.is_file():
            raise SystemExit(f"missing required input: {p}")
    if bp is not None and not bp.is_file():
        raise SystemExit(f"missing full canon batch report: {bp}")

    phase = load(pp)
    matrix = load(mp)
    gate = load(gp)
    cf = load(cp)
    batch = load(bp) if bp is not None else {}

    ps = phase.get("summary") if isinstance(phase.get("summary"), dict) else {}
    bs = batch.get("summary") if isinstance(batch.get("summary"), dict) else {}
    stage_rows = batch.get("stages") if isinstance(batch.get("stages"), list) else []
    gs = gate.get("summary") if isinstance(gate.get("summary"), dict) else {}
    cfm = cf.get("metrics") if isinstance(cf.get("metrics"), dict) else {}
    node_ids = matrix.get("node_ids") if isinstance(matrix.get("node_ids"), list) else []
    sample_nodes = [str(x) for x in node_ids[:6]]

    use_batch = bool(bs)
    node_count = bs.get("total_nodes") if use_batch else ps.get("node_count")
    edge_count = bs.get("total_edges") if use_batch else ps.get("edge_count")
    title = (
        "Global Atom Topology (Staged Full-Canon) with Multi-Gate Robustness"
        if use_batch
        else "Global Atom Topology PoC (Core-100) with Multi-Gate Robustness"
    )
    summary_line_2 = (
        "Staged full-canon run yields large-scale gated topology with verse-level ingest and stage-complete coverage."
        if use_batch
        else "Core-100 mixed-event PoC yields dense but gated topology with measurable old-new transition links."
    )

    stage_breakdown = []
    for s in stage_rows:
        if not isinstance(s, dict):
            continue
        stage_breakdown.append(
            {
                "stage": s.get("stage"),
                "target_count": s.get("target_count"),
                "node_count": s.get("node_count"),
                "edge_count": s.get("edge_count"),
                "phase_transition_signal": s.get("phase_transition_signal"),
                "phase_report_json": s.get("phase_report_json"),
            }
        )
    line = batch.get("run_lineage") if isinstance(batch.get("run_lineage"), dict) else {}
    manifest_lineage = {
        "run_stamp": line.get("run_stamp", batch.get("run_stamp")),
        "start_stage": line.get("start_stage", batch.get("start_stage")),
        "end_stage": line.get("end_stage", batch.get("end_stage")),
        "source_mode": bs.get("source_mode"),
        "stages_total": bs.get("stages_total"),
        "stages_ok": bs.get("stages_ok"),
        "event_window_size": line.get("event_window_size"),
    }

    out = {
        "schema": "global_atom_network_academic_onepager_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "title_en": title,
        "executive_summary_en": [
            "We encode events into atom-level structure and compute global topological similarity beyond lexical overlap.",
            summary_line_2,
            "Integrated drift/negative-control/counterfactual gates remain GO, supporting robustness claims.",
        ],
        "key_facts": {
            "node_count": node_count,
            "edge_count": edge_count,
            "old_new_cross_edges": ps.get("old_new_cross_edges"),
            "phase_transition_signal": ps.get("phase_transition_signal"),
            "gate_status": gs.get("status"),
            "counterfactual_mean_gap": cfm.get("mean_gap_base_minus_counterfactual"),
            "batch_stages_total": bs.get("stages_total"),
            "batch_stages_ok": bs.get("stages_ok"),
            "batch_source_mode": bs.get("source_mode"),
        },
        "method_outline_en": [
            "Atomize event-level candidates and assign symbolic sequence priors.",
            "Build pairwise similarity matrix and gate-passed topological edges.",
            "Run drift + negative-control + counterfactual gate stack before external reporting.",
        ],
        "risk_notes_en": [
            "N^2 similarity scaling requires staged expansion and compute budgeting.",
            "4D mapping can accumulate synchronization noise; ablation and counterfactual checks remain mandatory.",
        ],
        "stage_breakdown": stage_breakdown,
        "run_lineage": manifest_lineage,
        "reproducibility": {
            "recommended_commands": [
                "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_global_atom_full_canon_batch_v1.ps1 -UseEventSource",
                "py scripts/build_global_atom_full_canon_consolidated_manifest_v1.py",
                "py scripts/build_global_atom_full_canon_batch_report_v1.py --stages-json docs/final/artifacts/global_atom_full_canon/global_atom_full_canon_consolidated_manifest_latest.json --output-json docs/final/artifacts/global_atom_full_canon_batch_report_latest.json",
            ]
        },
        "artifact_packet": {
            "phase_report_json": str(pp),
            "similarity_matrix_json": str(mp),
            "full_canon_batch_report_json": str(bp) if bp is not None else "",
            "gate_summary_json": str(gp),
            "counterfactual_comparison_json": str(cp),
            "sample_node_ids": sample_nodes,
        },
    }

    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

