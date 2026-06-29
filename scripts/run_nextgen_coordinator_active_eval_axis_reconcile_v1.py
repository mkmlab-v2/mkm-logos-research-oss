#!/usr/bin/env python3
"""[HYPO] Phase v2.5 — reconcile ACTIVE evaluate_report axis vs coordinator hybrid payload axis."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report
from scripts.run_nextgen_coordinator_science_loss_sweep_v1 import (
    ACTIVE,
    BENCH,
    OUT_DEFAULT as SWEEP_DEFAULT,
    _eval_point,
    _frozen,
)
from scripts.nextgen_science_prior_terms_v1 import load_trilane_prior_terms

OUT_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_coordinator_active_eval_axis_reconcile_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _active_run_config() -> dict[str, Any]:
    if not ACTIVE.is_file():
        return {}
    return json.loads(ACTIVE.read_text(encoding="utf-8-sig")).get("run_config") or {}


def _run_active_evaluate_report(bench_doc: dict[str, Any], rc: dict[str, Any]) -> dict[str, Any]:
    lex_path = rc.get("master_codebook_lexicon_path")
    report = evaluate_report(
        bench_doc,
        source_input=str(BENCH.relative_to(ROOT)).replace("\\", "/"),
        mode=str(rc.get("mode", "experimental")),
        strategy=str(rc.get("strategy", "A")),
        intensity=str(rc.get("intensity", "extreme")),
        must_keep=set(rc.get("must_keep_terms") or []),
        general_max_saving_rate=float(rc.get("general_max_saving_rate", 0.35)),
        sensitive_max_saving_rate=float(rc.get("sensitive_max_saving_rate", 0.3)),
        hangul_max_saving_rate=float(rc.get("hangul_max_saving_rate", 0.6)),
        use_hangul_principle=bool(rc.get("use_hangul_principle", False)),
        use_domain_router=bool(rc.get("use_domain_router", True)),
        use_master_codebook_lexicon_v1=bool(rc.get("use_master_codebook_lexicon_v1", True)),
        include_gematria_metadata=bool(rc.get("include_gematria_metadata", False)),
        include_gematria_4d_bridge=bool(rc.get("include_gematria_4d_bridge", False)),
        include_cee_core=bool(rc.get("include_cee_core", False)),
        apply_gematria_4d_bridge_policy=bool(rc.get("apply_gematria_4d_bridge_policy", False)),
        domain_relaxed_max_saving_overrides=rc.get("domain_relaxed_max_saving_overrides"),
        domain_relaxed_max_saving_case_allowlist=rc.get(
            "domain_relaxed_max_saving_case_allowlist"
        ),
        domain_relaxed_max_saving_exclude_case_ids=rc.get(
            "domain_relaxed_max_saving_exclude_case_ids"
        ),
        master_codebook_lexicon_path=Path(lex_path) if lex_path else None,
    )
    cm = report.get("compression_metrics") or {}
    return {
        "axis": "track_a_evaluate_report",
        "global_token_saving_rate": cm.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": cm.get(
            "avg_reconstruction_fidelity_jaccard"
        ),
        "case_count": cm.get("case_count"),
        "note_ko": "동일 Golden-40 · ACTIVE run_config · evaluate_report 축",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sweep-json", type=Path, default=SWEEP_DEFAULT)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    if not BENCH.is_file():
        print(json.dumps({"error": "missing_bench"}))
        return 2

    bench_doc = json.loads(BENCH.read_text(encoding="utf-8-sig"))
    cases = bench_doc.get("compression_cases") or []
    rc = _active_run_config()
    active_axis = _run_active_evaluate_report(bench_doc, rc)

    sweep = (
        json.loads(args.sweep_json.read_text(encoding="utf-8-sig"))
        if args.sweep_json.is_file()
        else {}
    )
    best = sweep.get("best_by_loss") or {}
    kr = float(best.get("keep_ratio", 0.86))
    sw = float(best.get("science_weight_scale", 0.7))
    w_s = float(best.get("w_s", 0.8))
    w_j = float(best.get("w_j", 1.0))

    all_terms, _ = load_trilane_prior_terms(root=ROOT, merge_archetype=True)
    from scripts.nextgen_science_prior_terms_v1 import load_science_prior_terms

    science_terms, _ = load_science_prior_terms(root=ROOT)
    from scripts.nextgen_coordinator_science_loss_v1 import load_kernel_defaults

    spec = ROOT / "experiments/nextgen_clean_slate_cpu_v1/COORDINATOR_SCIENCE_KERNEL_V2.json"
    defaults = load_kernel_defaults(spec)
    hybrid_row = _eval_point(
        cases,
        keep_ratio=kr,
        science_weight_scale=sw,
        w_s=w_s,
        w_j=w_j,
        all_terms=all_terms,
        science_terms=science_terms,
        defaults=defaults,
    )

    fr = _frozen()
    hybrid_axis = {
        "axis": "coordinator_hybrid_spine_trilane_payload",
        "payload_global_token_saving_rate": hybrid_row.get(
            "payload_global_token_saving_rate"
        ),
        "avg_sidecar_jaccard": hybrid_row.get("avg_sidecar_jaccard"),
        "avg_lens_disagreement": hybrid_row.get("avg_lens_disagreement"),
        "byte_exact_subset_parity": hybrid_row.get("byte_exact_subset_parity"),
        "knobs": {
            "keep_ratio": kr,
            "science_weight_scale": sw,
            "w_s": w_s,
            "w_j": w_j,
        },
        "note_ko": "spine+sidecar 바이트 합산 [HYPO] — ACTIVE global_token_saving_rate와 다른 축",
    }

    a_s = active_axis.get("global_token_saving_rate")
    a_j = active_axis.get("avg_reconstruction_fidelity_jaccard")
    h_s = hybrid_axis.get("payload_global_token_saving_rate")
    h_j = hybrid_axis.get("avg_sidecar_jaccard")

    out = {
        "schema": "nextgen_coordinator_active_eval_axis_reconcile_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "frozen_active": fr,
        "active_evaluate_report_axis": active_axis,
        "coordinator_hybrid_axis": hybrid_axis,
        "delta_hybrid_minus_active": {
            "saving_pp": round((float(h_s) - float(a_s)) * 100, 2)
            if h_s is not None and a_s is not None
            else None,
            "jaccard_pp": round((float(h_j) - float(a_j)) * 100, 2)
            if h_j is not None and a_j is not None
            else None,
        },
        "conflation_guard": {
            "axes_comparable": False,
            "reason_ko": "evaluate_report 토큰 경로 vs spine+trilane 바이트 경로 — headline 단일 수치 금지",
        },
        "dual_axis_beat_on_hybrid": hybrid_row.get("dual_axis_beat"),
        "promotion_implication": "research_only_no_track_a_write",
        "pointers": {
            "active_report": str(ACTIVE.relative_to(ROOT)).replace("\\", "/"),
            "sweep": str(args.sweep_json.relative_to(ROOT)).replace("\\", "/")
            if args.sweep_json.is_file()
            else None,
        },
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "active_saving": a_s,
                "hybrid_payload_saving": h_s,
                "dual_axis_beat": hybrid_row.get("dual_axis_beat"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
