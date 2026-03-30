#!/usr/bin/env python3
"""Grid search bridge-aware scoring weights for saving/fidelity trade-off."""

from __future__ import annotations

import itertools
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report


INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_GEMATRIA_4D_BRIDGE_WEIGHT_SWEEP_V1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _score_candidate(row: dict) -> tuple[float, float, float]:
    # prioritize: gate-pass first, then higher fidelity, then higher saving
    gate = 1.0 if bool(row.get("joint_target_ok")) else 0.0
    return (gate, float(row.get("avg_reconstruction_fidelity_jaccard", 0.0)), float(row.get("global_token_saving_rate", 0.0)))


def main() -> int:
    src = _load(INPUT_V2)
    base = _load(BASELINE_V2)
    dec = _load(DECISION)
    selected = dec.get("selected_candidate") or {}

    strategy = str(selected.get("strategy", "A"))
    intensity = str(selected.get("intensity", "extreme"))
    baseline_avg_jaccard = float(base.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0))
    threshold_pp = float(dec.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))
    threshold_saving = 0.50
    threshold_fidelity = 0.75

    weight_grid = {
        "fidelity": [0.8, 1.0, 1.2, 1.4],
        "guard": [0.2, 0.4, 0.6],
        "saving": [0.4, 0.6, 0.8, 1.0],
        "distance_penalty": [0.5, 1.0, 2.0, 4.0],
    }

    rows = []
    for f, g, s, d in itertools.product(
        weight_grid["fidelity"],
        weight_grid["guard"],
        weight_grid["saving"],
        weight_grid["distance_penalty"],
    ):
        weights = {"fidelity": f, "guard": g, "saving": s, "distance_penalty": d}
        rep = evaluate_report(
            src,
            source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
            mode="experimental",
            strategy=strategy,
            intensity=intensity,
            must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
            jaccard_drop_threshold_pp=threshold_pp,
            baseline_avg_jaccard=baseline_avg_jaccard,
            general_max_saving_rate=(
                float(selected["general_max_saving_rate"]) if selected.get("general_max_saving_rate") is not None else None
            ),
            sensitive_max_saving_rate=(
                float(selected["sensitive_max_saving_rate"]) if selected.get("sensitive_max_saving_rate") is not None else None
            ),
            hangul_max_saving_rate=(
                float(selected["hangul_max_saving_rate"]) if selected.get("hangul_max_saving_rate") is not None else None
            ),
            use_domain_router=True,
            include_gematria_metadata=True,
            include_gematria_4d_bridge=True,
            apply_gematria_4d_bridge_policy=True,
            use_contextual_generator_v2=True,
            use_contextual_generator_v3=True,
            use_contextual_generator_v4=True,
            use_contextual_generator_v5_codec=True,
            bridge_score_weights=weights,
        )
        cm = rep.get("compression_metrics", {})
        q = rep.get("quality_gate", {})
        saving = float(cm.get("global_token_saving_rate", 0.0))
        fidelity = float(cm.get("avg_reconstruction_fidelity_jaccard", 0.0))
        row = {
            "weights": weights,
            "global_token_saving_rate": saving,
            "avg_reconstruction_fidelity_jaccard": fidelity,
            "avg_sensitive_integrity": float(cm.get("avg_sensitive_integrity", 0.0)),
            "jaccard_guardrail_ok": bool(q.get("jaccard_guardrail_ok")),
            "sensitive_integrity_ok": bool(q.get("sensitive_integrity_ok")),
            "joint_target_ok": (
                saving >= threshold_saving
                and fidelity >= threshold_fidelity
                and bool(q.get("jaccard_guardrail_ok"))
                and bool(q.get("sensitive_integrity_ok"))
            ),
        }
        rows.append(row)

    ranked = sorted(rows, key=_score_candidate, reverse=True)
    best = ranked[0] if ranked else None
    passing = [r for r in ranked if r.get("joint_target_ok")]

    out = {
        "schema": "multilens_gematria_4d_bridge_weight_sweep_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "source_input": "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        "profile": {"strategy": strategy, "intensity": intensity},
        "target": {"saving_min": threshold_saving, "fidelity_min": threshold_fidelity, "jaccard_drop_threshold_pp": threshold_pp},
        "grid_size": len(rows),
        "pass_count": len(passing),
        "best_candidate": best,
        "top5": ranked[:5],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
