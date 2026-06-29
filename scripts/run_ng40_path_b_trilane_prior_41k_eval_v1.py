#!/usr/bin/env python3
"""[HYPO] Path B structure: 41k ON + Logos/science/sasang tri-lane prior must_keep vs ACTIVE."""
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

from scripts.nextgen_science_prior_terms_v1 import DEFAULT_SPEC, load_trilane_prior_terms
from scripts.run_nextgen_latent_indexer_eval_ng40_v1 import (  # noqa: E402
    INPUT_V2,
    _beat,
    _frozen_active,
    evaluate_ng40_lane,
)

KNEE_41K = ROOT / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_41k_on_best_v1_latest.json"
SALIENCE_HOOK = (
    ROOT / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_salience_hook_only.json"
)
NAV_FRAME = ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_NAV_FRAME_V1.json"
SCIENCE_SPEC = ROOT / DEFAULT_SPEC
OUT_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_path_b_trilane_prior_41k_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _caps_from_knee() -> tuple[float, float, float, bool]:
    if KNEE_41K.is_file():
        rc = json.loads(KNEE_41K.read_text(encoding="utf-8-sig")).get("run_config_summary") or {}
        return (
            float(rc.get("general_max_saving_rate", 0.32)),
            float(rc.get("sensitive_max_saving_rate", 0.28)),
            float(rc.get("hangul_max_saving_rate", 0.55)),
            bool(rc.get("with_domain_relaxed", False)),
        )
    return 0.32, 0.28, 0.55, False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--bench-input", type=Path, default=INPUT_V2)
    args = ap.parse_args()

    if not args.bench_input.is_file():
        print(json.dumps({"error": "missing_bench_input"}))
        return 2

    g, s, h, relaxed = _caps_from_knee()
    prior_terms, prior_meta = load_trilane_prior_terms(
        root=ROOT,
        spec_path=SCIENCE_SPEC,
        salience_hook_path=SALIENCE_HOOK,
        nav_frame_path=NAV_FRAME,
        logos_pack_path=None,
        merge_archetype=True,
    )
    doc = json.loads(args.bench_input.read_text(encoding="utf-8-sig"))
    baseline_j = 0.0
    baseline_path = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
    if baseline_path.is_file():
        bdoc = json.loads(baseline_path.read_text(encoding="utf-8-sig"))
        baseline_j = float(
            bdoc.get("compression_metrics", {}).get(
                "avg_reconstruction_fidelity_jaccard", 0.0
            )
        )

    agg, report = evaluate_ng40_lane(
        doc,
        bench_input=args.bench_input,
        general_cap=g,
        sensitive_cap=s,
        hangul_cap=h,
        baseline_j=baseline_j,
        use_domain_relaxed=relaxed,
        use_master_codebook_lexicon_v1=True,
        active_track_parity=True,
        archetype_prior_must_keep=prior_terms,
    )
    frozen = _frozen_active()
    beat = _beat(agg, frozen)
    report_path = args.out_json.parent / f"{args.out_json.stem}.report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    archetype_only = ROOT / (
        "experiments/nextgen_clean_slate_cpu_v1/results/"
        "ng40_latent_eval_path_b_prior_41k_v1_latest.json"
    )
    delta_note: dict[str, Any] = {}
    if archetype_only.is_file():
        a = json.loads(archetype_only.read_text(encoding="utf-8-sig")).get("aggregate") or {}
        delta_note = {
            "vs_archetype_only_41k": {
                "saving_delta": round(
                    float(agg.get("global_token_saving_rate", 0))
                    - float(a.get("global_token_saving_rate", 0)),
                    6,
                ),
                "jaccard_delta": round(
                    float(agg.get("avg_reconstruction_fidelity_jaccard", 0))
                    - float(a.get("avg_reconstruction_fidelity_jaccard", 0)),
                    6,
                ),
            }
        }

    out = {
        "schema": "nextgen_latent_eval_ng40_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "path_b_lane": True,
        "structure_experiment": True,
        "arm_id": "ng40_latent_eval_path_b_trilane_prior_41k_v1",
        "lane": "path_b_41k_on + trilane_prior_must_keep (structure)",
        "aggregate": agg,
        "frozen_baseline_active": frozen,
        "beat_check": beat,
        "prior_terms_count": len(prior_terms),
        "prior_terms_meta": prior_meta,
        "delta_vs_prior_arms": delta_note,
        "run_config_summary": {
            "general_max_saving_rate": g,
            "sensitive_max_saving_rate": s,
            "hangul_max_saving_rate": h,
            "with_domain_relaxed": relaxed,
            "use_master_codebook_lexicon_v1": True,
            "active_track_parity": True,
            "trilane_prior_must_keep": True,
        },
        "report_pointer": str(report_path.relative_to(ROOT)).replace("\\", "/"),
        "knee_reference": str(KNEE_41K.relative_to(ROOT)).replace("\\", "/"),
        "guardrails": [
            "beat_check vs ACTIVE only",
            "No Track A write",
            "Not cap sweep — policy mask structure",
        ],
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "beat_frozen": beat.get("beat_frozen"),
                "saving": agg.get("global_token_saving_rate"),
                "jaccard": agg.get("avg_reconstruction_fidelity_jaccard"),
                "prior_terms": len(prior_terms),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
