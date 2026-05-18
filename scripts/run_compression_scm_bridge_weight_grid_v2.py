#!/usr/bin/env python3
"""RQ-016 phase-2: fine grid around scm selective bridge + saving_heavy weights (floor 47%)."""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report

INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
OUT_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "compression_scm_bridge_weight_grid_v2_latest.json"
POLICY_FLOOR = 0.47
SCM_IDS = frozenset({"cmp2_015", "cmp2_023", "cmp2_028"})
HEALTH_ID = "cmp2_014"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _row_metrics(report: dict[str, Any]) -> dict[str, Any]:
    cm = report.get("compression_metrics") or {}
    saving = float(cm.get("global_token_saving_rate") or 0)
    avg_j = float(cm.get("avg_reconstruction_fidelity_jaccard") or 0)
    cases = cm.get("cases") or []
    scm_rows = [c for c in cases if str(c.get("id", "")) in SCM_IDS]
    scm_min = (
        min(float(r.get("reconstruction_fidelity_jaccard") or 0) for r in scm_rows) if scm_rows else None
    )
    health_row = next((c for c in cases if str(c.get("id", "")) == HEALTH_ID), None)
    health_j = (
        float(health_row.get("reconstruction_fidelity_jaccard") or 0) if health_row else None
    )
    return {
        "global_token_saving_rate": saving,
        "ultra_saving_policy_ok": saving >= POLICY_FLOOR,
        "avg_reconstruction_fidelity_jaccard": avg_j,
        "scm_min_jaccard": scm_min,
        "health_jaccard": health_j,
    }


def _rank_key(row: dict[str, Any]) -> tuple:
    """Floor pass first, then higher saving, then scm min jaccard, then avg jaccard."""
    floor = 1 if row.get("ultra_saving_policy_ok") else 0
    return (
        floor,
        float(row.get("global_token_saving_rate") or 0),
        float(row.get("scm_min_jaccard") or 0),
        float(row.get("avg_reconstruction_fidelity_jaccard") or 0),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    src = _load(INPUT_V2)
    base = _load(BASELINE_V2)
    dec = _load(DECISION)
    sel = dec.get("selected_candidate") or {}
    baseline_j = float(base.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0))
    threshold_pp = float(dec.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))

    def _gms(x: Any) -> float | None:
        return float(x) if x is not None else None

    common = dict(
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=str(sel.get("strategy", "A")),
        intensity=str(sel.get("intensity", "extreme")),
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_j,
        general_max_saving_rate=_gms(sel.get("general_max_saving_rate")),
        sensitive_max_saving_rate=_gms(sel.get("sensitive_max_saving_rate")),
        hangul_max_saving_rate=_gms(sel.get("hangul_max_saving_rate")),
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        include_cee_core=True,
    )

    baseline_rep = evaluate_report(
        src,
        **common,
        apply_gematria_4d_bridge_policy=False,
        bridge_policy_domain_allowlist=None,
        bridge_score_weights=None,
    )
    baseline_m = _row_metrics(baseline_rep)
    baseline_avg = baseline_m["avg_reconstruction_fidelity_jaccard"]

    # saving_heavy center + neighborhood (phase-2)
    grid = {
        "fidelity": [0.85, 1.0, 1.15],
        "guard": [0.35, 0.4, 0.5],
        "saving": [0.55, 0.65, 0.75, 0.85, 0.95],
        "distance_penalty": [1.0, 1.5, 2.0, 2.5],
    }

    results: list[dict[str, Any]] = [
        {
            "id": "baseline_bridge_off",
            "weights": None,
            "allowlist": None,
            **baseline_m,
            "delta_avg_jaccard_vs_baseline": 0.0,
        }
    ]

    for f, g, s, d in itertools.product(
        grid["fidelity"],
        grid["guard"],
        grid["saving"],
        grid["distance_penalty"],
    ):
        weights = {"fidelity": f, "guard": g, "saving": s, "distance_penalty": d}
        rep = evaluate_report(
            src,
            **common,
            apply_gematria_4d_bridge_policy=True,
            bridge_policy_domain_allowlist=frozenset({"scm"}),
            bridge_score_weights=weights,
        )
        m = _row_metrics(rep)
        results.append(
            {
                "id": f"scm_w_f{f}_g{g}_s{s}_d{d}",
                "weights": weights,
                "allowlist": ["scm"],
                **m,
                "delta_avg_jaccard_vs_baseline": round(
                    float(m["avg_reconstruction_fidelity_jaccard"]) - baseline_avg, 6
                ),
            }
        )

    ranked = sorted(results[1:], key=_rank_key, reverse=True)
    floor_pass = [r for r in ranked if r.get("ultra_saving_policy_ok")]
    scm_lift = [
        r
        for r in ranked
        if (r.get("scm_min_jaccard") or 0) > (baseline_m.get("scm_min_jaccard") or 0)
    ]
    best_floor = floor_pass[0] if floor_pass else None
    best_tradeoff = scm_lift[0] if scm_lift else ranked[0] if ranked else None

    doc = {
        "schema": "compression_scm_bridge_weight_grid_v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "hypothesis_tier": "B",
        "track_wall": "b_track_research_only",
        "rq": "RQ-016",
        "policy_floor": POLICY_FLOOR,
        "baseline": baseline_m,
        "grid_size": len(results) - 1,
        "floor_pass_count": len(floor_pass),
        "best_at_floor": best_floor,
        "best_scm_lift_near_floor": best_tradeoff,
        "top10_by_rank": ranked[:10],
        "pareto_floor_and_scm": [
            r
            for r in ranked
            if r.get("ultra_saving_policy_ok")
            and (r.get("scm_min_jaccard") or 0) >= (baseline_m.get("scm_min_jaccard") or 0)
        ][:15],
        "recommendation": (
            "promote_weight_candidate_for_b_track_only"
            if best_floor
            else "no_joint_floor_scm_pareto_yet_keep_track_a_frozen"
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(args.out),
                "grid_size": doc["grid_size"],
                "floor_pass_count": doc["floor_pass_count"],
                "recommendation": doc["recommendation"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
