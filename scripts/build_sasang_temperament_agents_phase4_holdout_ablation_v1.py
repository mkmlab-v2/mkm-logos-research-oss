#!/usr/bin/env python3
"""RQ-026 phase-4: chronological holdout + matrix vs no-matrix ablation ([HYPO])."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = (
    ROOT / "experiments/sasang_temperament_agents_v1/specs/temperament_agent_state_v1.example.json"
)
DEFAULT_MATRIX = (
    ROOT / "experiments/sasang_temperament_agents_v1/specs/pathology_transition_matrix_v1_2.json"
)
DEFAULT_INPUT = ROOT / "reports/btrack_per_date_directions_market_psych_v2.json"
DEFAULT_OUT = (
    ROOT / "docs/final/artifacts/sasang_temperament_agents_phase4_holdout_ablation_v1_latest.json"
)
REPORT_OUT = ROOT / "reports/sasang_temperament_agents_phase4_holdout_ablation_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_run_sim():
    sim_path = ROOT / "scripts/run_sasang_temperament_agents_sim_stub_v1.py"
    spec = importlib.util.spec_from_file_location("rq026_sim_stub", sim_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import sim stub: {sim_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["rq026_sim_stub"] = mod
    spec.loader.exec_module(mod)
    return mod.run_sim


def _split_holdout(steps: list[dict[str, Any]], holdout_fraction: float) -> tuple[list, list]:
    ordered = sorted(steps, key=lambda s: str(s.get("eval_date") or ""))
    n = len(ordered)
    if n == 0:
        return [], []
    hold_n = max(1, int(round(n * holdout_fraction)))
    if hold_n >= n:
        hold_n = max(1, n // 5)
    return ordered[: n - hold_n], ordered[n - hold_n :]


def _consistency_from_steps(steps: list[dict[str, Any]]) -> dict[str, Any]:
    conflicts = [float(s.get("conflict_score") or 0.0) for s in steps]
    n = len(conflicts) or 1
    mean_conflict = sum(conflicts) / n
    consensus_days = sum(1 for s in steps if s.get("consensus_day"))
    score = round(max(0.0, min(1.0, 1.0 - mean_conflict)), 6)
    return {
        "score": score,
        "mean_conflict_score": round(mean_conflict, 6),
        "consensus_day_rate": round(consensus_days / n, 6),
        "n_days": n,
    }


def _replay_from_steps(steps: list[dict[str, Any]]) -> dict[str, Any]:
    hits = 0
    total = 0
    for step in steps:
        for agent in step.get("agents") or []:
            if not isinstance(agent, dict):
                continue
            total += 1
            if agent.get("transition_replay_ok"):
                hits += 1
    rate = round(hits / total, 6) if total else 0.0
    return {"replay_match_rate": rate, "replay_hits": hits, "replay_total": total}


def _slice_metrics(steps: list[dict[str, Any]], matrix: dict[str, Any]) -> dict[str, Any]:
    phase2_path = ROOT / "scripts/build_sasang_temperament_agents_phase2_eval_v1.py"
    spec = importlib.util.spec_from_file_location("rq026_phase2_eval", phase2_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import phase2 eval: {phase2_path}")
    phase2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(phase2)
    dominance = phase2.dominance_metrics_from_steps(steps, matrix)
    return {
        "temperament_consistency": _consistency_from_steps(steps),
        "pathology_transition_replay": _replay_from_steps(steps),
        "constitution_pathology_dominance": dominance,
    }


def build(
    *,
    spec: dict[str, Any],
    matrix: dict[str, Any],
    env_rows: list[dict[str, Any]],
    holdout_fraction: float,
    run_sim,
) -> dict[str, Any]:
    sim_matrix = run_sim(spec=spec, env_rows=env_rows, max_days=None, matrix=matrix)
    sim_none = run_sim(spec=spec, env_rows=env_rows, max_days=None, matrix=None)

    train_m, hold_m = _split_holdout(sim_matrix.get("daily_steps") or [], holdout_fraction)
    train_n, hold_n = _split_holdout(sim_none.get("daily_steps") or [], holdout_fraction)

    holdout_matrix = _slice_metrics(hold_m, matrix)
    holdout_none = _slice_metrics(hold_n, matrix)
    full_matrix = {
        "temperament_consistency": (sim_matrix.get("eval_axes") or {}).get("temperament_consistency"),
        "pathology_transition_replay": (sim_matrix.get("eval_axes") or {}).get(
            "pathology_transition_replay"
        ),
    }
    full_none = {
        "temperament_consistency": (sim_none.get("eval_axes") or {}).get("temperament_consistency"),
        "pathology_transition_replay": (sim_none.get("eval_axes") or {}).get(
            "pathology_transition_replay"
        ),
    }

    fear_m = holdout_matrix["constitution_pathology_dominance"].get(
        "fear_constitution_dominant_on_aggravating_rate"
    )
    fear_n = holdout_none["constitution_pathology_dominance"].get(
        "fear_constitution_dominant_on_aggravating_rate"
    )
    cons_m = holdout_matrix["temperament_consistency"]["score"]
    cons_n = holdout_none["temperament_consistency"]["score"]

    threshold = float(
        (matrix.get("dominance_rules") or {}).get(
            "taeeum_or_soeumin_fear_share_on_aggravating_min", 0.45
        )
    )
    hold_m_pass = holdout_matrix["constitution_pathology_dominance"].get("fear_dominance_pass")
    hold_n_pass = holdout_none["constitution_pathology_dominance"].get("fear_dominance_pass")

    doc: dict[str, Any] = {
        "schema": "sasang_temperament_agents_phase4_holdout_ablation_v1",
        "generated_at_utc": _utc(),
        "rq_id": "RQ-026",
        "hypothesis_tier": "B",
        "research_only": True,
        "not_promoted_track_a": True,
        "holdout_fraction": holdout_fraction,
        "n_days_total": len(sim_matrix.get("daily_steps") or []),
        "n_days_train": len(train_m),
        "n_days_holdout": len(hold_m),
        "holdout_date_range": {
            "first": hold_m[0].get("eval_date") if hold_m else None,
            "last": hold_m[-1].get("eval_date") if hold_m else None,
        },
        "matrix_coupled": {
            "pathology_matrix_coupled": True,
            "full_eval_axes": full_matrix,
            "holdout_eval_axes": holdout_matrix,
        },
        "no_matrix_legacy": {
            "pathology_matrix_coupled": False,
            "full_eval_axes": full_none,
            "holdout_eval_axes": holdout_none,
        },
        "ablation_delta_holdout": {
            "fear_dominance_rate_matrix_minus_none": round((fear_m or 0) - (fear_n or 0), 6),
            "temperament_consistency_matrix_minus_none": round(cons_m - cons_n, 6),
            "matrix_improves_holdout_fear_dominance": (fear_m or 0) >= (fear_n or 0),
        },
        "holdout_gates": {
            "fear_dominance_threshold": threshold,
            "matrix_coupled_pass": hold_m_pass,
            "no_matrix_pass": hold_n_pass,
            "both_pass": hold_m_pass is True and hold_n_pass is True,
        },
        "verdict_ko": (
            "holdout+matrix ablation 기록됨; matrix coupling이 holdout fear dominance에 기여."
            if (fear_m or 0) >= (fear_n or 0) and hold_m_pass is True
            else "holdout ablation 기록됨; matrix/no-matrix 비교만 — 승격·임상 단정 없음."
        ),
        "note_ko": "시간순 holdout; OHLCV·Jaccard·Track A와 무관. sim 점수만으로 CLOSED 불가.",
    }
    return doc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--also-report", action="store_true", help="mirror to reports/")
    ap.add_argument("--holdout-fraction", type=float, default=0.2)
    ap.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 if matrix holdout fear_dominance_pass is not true",
    )
    args = ap.parse_args()

    for p, name in ((args.spec, "spec"), (args.matrix, "matrix"), (args.input, "input")):
        if not p.is_file():
            raise SystemExit(f"missing {name}: {p}")

    if not 0.05 <= args.holdout_fraction <= 0.5:
        raise SystemExit("holdout-fraction must be between 0.05 and 0.5")

    spec = _load(args.spec)
    matrix = _load(args.matrix)
    env_doc = _load(args.input)
    rows = [r for r in env_doc.get("rows") or [] if isinstance(r, dict)]
    if not rows:
        raise SystemExit("no environment rows")

    run_sim = _load_run_sim()
    doc = build(
        spec=spec,
        matrix=matrix,
        env_rows=rows,
        holdout_fraction=args.holdout_fraction,
        run_sim=run_sim,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.out)
    if args.also_report:
        REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
        REPORT_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(REPORT_OUT)

    if args.strict and doc.get("holdout_gates", {}).get("matrix_coupled_pass") is not True:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
