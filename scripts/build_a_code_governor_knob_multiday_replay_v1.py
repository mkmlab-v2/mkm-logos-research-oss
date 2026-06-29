#!/usr/bin/env python3
"""RQ-028 phase-4 style: multi-day governor knob replay + pathology ablation ([HYPO])."""
from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "experiments/a_code_12ai_v2/specs/a_code_12ai_matrix_v2.example.json"
DEFAULT_PATHOLOGY = (
    ROOT / "experiments/sasang_temperament_agents_v1/specs/pathology_transition_matrix_v1_2.json"
)
DEFAULT_PATHOLOGY_BASELINE = (
    ROOT / "experiments/sasang_temperament_agents_v1/specs/pathology_transition_matrix_v1_1.json"
)
DEFAULT_SESSION_PANEL = ROOT / "reports/btrack_session_myeongni_panel_202606_june_prophecy.csv"
DEFAULT_MARKET_PSYCH = ROOT / "reports/btrack_per_date_directions_market_psych_v2.json"
DEFAULT_OUT = ROOT / "reports/a_code_governor_knob_multiday_replay_v1_latest.json"

FORBIDDEN_KEYS = frozenset(
    {
        "price_directional_hit_rate",
        "jaccard",
        "saving_pct",
        "live_trading",
        "dual_axis_beat",
    }
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _import_profile_resolver():
    path = ROOT / "scripts/a_code_commander_profile_resolve_v1.py"
    spec = importlib.util.spec_from_file_location("a_code_profile_resolve", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import profile resolver: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _import_governor_sim():
    sim_path = ROOT / "scripts/run_a_code_governor_knob_sim_stub_v1.py"
    spec = importlib.util.spec_from_file_location("a_code_governor_sim", sim_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import governor sim: {sim_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["a_code_governor_sim"] = mod
    spec.loader.exec_module(mod)
    return mod


def _split_holdout(dates: list[str], holdout_fraction: float) -> tuple[list[str], list[str]]:
    ordered = sorted(dates)
    n = len(ordered)
    if n == 0:
        return [], []
    hold_n = max(1, int(round(n * holdout_fraction)))
    if hold_n >= n:
        hold_n = max(1, n // 5)
    return ordered[: n - hold_n], ordered[n - hold_n :]


def _daily_row(
    *,
    session_date: str,
    session_row: dict[str, str],
    matrix: dict[str, Any],
    profile: dict[str, Any],
    pathology_matrix: dict[str, Any] | None,
    transition_hint: str | None,
    mode: str,
) -> dict[str, Any]:
    mod = _import_governor_sim()
    knob = mod.compute_knobs(
        matrix=matrix,
        profile=profile,
        session_row=session_row,
        pathology_matrix=pathology_matrix or {},
        transition_hint=transition_hint,
    )
    payload = {
        "session_date": session_date,
        "mode": mode,
        "adjusted_knobs": knob["adjusted_knobs"],
        "governor_knob_delta": knob["governor_knob_delta"],
        "drivers": knob["drivers"],
        "day_pillar": session_row.get("day_pillar"),
    }
    fp = mod._deterministic_fingerprint(payload)
    return {**payload, "deterministic_fingerprint": fp}


def _series_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n_days": 0}
    lambdas = [float(r["adjusted_knobs"]["token_budget_lambda"]) for r in rows]
    parallels = [int(r["adjusted_knobs"]["parallel_cap"]) for r in rows]
    path_caps = [float(r["adjusted_knobs"]["pathology_gain_cap"]) for r in rows]
    lambda_deltas = [float(r["governor_knob_delta"]["token_budget_lambda_delta"]) for r in rows]
    replay_ok = 0
    mod = _import_governor_sim()
    for r in rows:
        fp2 = mod._deterministic_fingerprint(
            {
                "session_date": r["session_date"],
                "mode": r["mode"],
                "adjusted_knobs": r["adjusted_knobs"],
                "governor_knob_delta": r["governor_knob_delta"],
                "drivers": r["drivers"],
                "day_pillar": r.get("day_pillar"),
            }
        )
        if fp2 == r["deterministic_fingerprint"]:
            replay_ok += 1
    n = len(rows)
    return {
        "n_days": n,
        "orchestration_consistency_rate": round(replay_ok / n, 6),
        "mean_token_budget_lambda": round(statistics.mean(lambdas), 6),
        "mean_parallel_cap": round(statistics.mean(parallels), 6),
        "mean_pathology_gain_cap": round(statistics.mean(path_caps), 6),
        "mean_token_budget_lambda_delta": round(statistics.mean(lambda_deltas), 6),
        "stdev_token_budget_lambda": round(statistics.pstdev(lambdas), 6) if n > 1 else 0.0,
    }


def build(
    *,
    matrix: dict[str, Any],
    profile: dict[str, Any],
    session_rows: list[dict[str, str]],
    pathology_v12: dict[str, Any],
    pathology_v11: dict[str, Any],
    hint_index: dict[str, str],
    holdout_fraction: float,
) -> dict[str, Any]:
    dates = [str(r.get("session_local_date") or "") for r in session_rows if r.get("session_local_date")]
    train_dates, holdout_dates = _split_holdout(dates, holdout_fraction)
    date_to_row = {str(r["session_local_date"]): r for r in session_rows}

    def run_mode(pathology: dict[str, Any] | None, mode: str, use_hints: bool) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for d in dates:
            hint = hint_index.get(d) if use_hints else None
            out.append(
                _daily_row(
                    session_date=d,
                    session_row=date_to_row[d],
                    matrix=matrix,
                    profile=profile,
                    pathology_matrix=pathology,
                    transition_hint=hint,
                    mode=mode,
                )
            )
        return out

    pathology_on = run_mode(pathology_v12, "pathology_v1_2_on", use_hints=True)
    pathology_off = run_mode(None, "pathology_off", use_hints=False)
    pathology_v11_rows = run_mode(pathology_v11, "pathology_v1_1_on", use_hints=True)

    def slice_rows(rows: list[dict[str, Any]], subset: set[str]) -> list[dict[str, Any]]:
        return [r for r in rows if r["session_date"] in subset]

    train_set = set(train_dates)
    holdout_set = set(holdout_dates)

    on_train = _series_metrics(slice_rows(pathology_on, train_set))
    on_holdout = _series_metrics(slice_rows(pathology_on, holdout_set))
    off_all = _series_metrics(pathology_off)
    v11_all = _series_metrics(pathology_v11_rows)

    ablation_pairs: list[dict[str, Any]] = []
    for on_row, off_row in zip(pathology_on, pathology_off, strict=True):
        d = on_row["session_date"]
        cap_on = float(on_row["adjusted_knobs"]["pathology_gain_cap"])
        cap_off = float(off_row["adjusted_knobs"]["pathology_gain_cap"])
        ablation_pairs.append(
            {
                "session_date": d,
                "pathology_gain_cap_on": cap_on,
                "pathology_gain_cap_off": cap_off,
                "pathology_gain_cap_ablation_delta": round(cap_on - cap_off, 6),
            }
        )

    cap_ablation_deltas = [p["pathology_gain_cap_ablation_delta"] for p in ablation_pairs]
    mean_ablation = round(statistics.mean(cap_ablation_deltas), 6) if cap_ablation_deltas else 0.0

    v12_caps = [float(r["adjusted_knobs"]["pathology_gain_cap"]) for r in pathology_on]
    v11_caps = [float(r["adjusted_knobs"]["pathology_gain_cap"]) for r in pathology_v11_rows]
    matrix_variant_delta = (
        round(statistics.mean([a - b for a, b in zip(v12_caps, v11_caps, strict=True)]), 6)
        if v12_caps
        else 0.0
    )

    return {
        "schema": "a_code_governor_knob_multiday_replay_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "rq_id": "RQ-028",
        "hypothesis_tier": "B",
        "research_only": True,
        "holdout_fraction": holdout_fraction,
        "n_session_days": len(dates),
        "train_dates": train_dates,
        "holdout_dates": holdout_dates,
        "eval_axes": {
            "governor_knob_delta": {
                "pathology_on_train": on_train,
                "pathology_on_holdout": on_holdout,
                "pathology_off_all": off_all,
            },
            "orchestration_consistency": {
                "train": on_train.get("orchestration_consistency_rate"),
                "holdout": on_holdout.get("orchestration_consistency_rate"),
            },
            "pathology_transition_replay": {
                "mean_pathology_gain_cap_ablation_delta": mean_ablation,
                "matrix_v1_2_vs_v1_1_mean_path_cap_delta": matrix_variant_delta,
            },
        },
        "ablation_summary": {
            "pathology_on_vs_off_mean_cap_delta": mean_ablation,
            "pathology_v1_2_vs_v1_1_mean_cap_delta": matrix_variant_delta,
            "hints_available_days": sum(1 for d in dates if d in hint_index),
        },
        "time_series": {
            "pathology_v1_2_on": pathology_on,
            "pathology_off": pathology_off,
            "pathology_v1_1_on": pathology_v11_rows,
        },
        "note_ko": "multi-day S2 노브 replay·pathology ablation. Track A·실매매·가격 승격 근거 아님.",
    }


def _assert_no_forbidden(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in FORBIDDEN_KEYS:
                raise ValueError(f"forbidden key: {path}.{k}")
            _assert_no_forbidden(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _assert_no_forbidden(item, f"{path}[{i}]")


def main() -> int:
    parser = argparse.ArgumentParser(description="A-code governor knob multiday replay + ablation")
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--profile", type=Path, default=None, help="default: local > MKM_COMMANDER_PROFILE_JSON > example")
    parser.add_argument("--pathology-matrix", type=Path, default=DEFAULT_PATHOLOGY)
    parser.add_argument("--pathology-matrix-baseline", type=Path, default=DEFAULT_PATHOLOGY_BASELINE)
    parser.add_argument("--session-panel", type=Path, default=DEFAULT_SESSION_PANEL)
    parser.add_argument("--market-psych", type=Path, default=DEFAULT_MARKET_PSYCH)
    parser.add_argument("--holdout-fraction", type=float, default=0.2)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    mod = _import_governor_sim()
    resolver = _import_profile_resolver()
    profile_path, profile_source = resolver.resolve_commander_profile_path(args.profile)
    matrix = _load(args.matrix)
    profile = _load(profile_path)
    pathology_v12 = _load(args.pathology_matrix)
    pathology_v11 = _load(args.pathology_matrix_baseline)
    session_rows = mod.read_session_panel_rows(args.session_panel)
    hint_index = mod.build_market_psych_hint_index(args.market_psych)

    report = build(
        matrix=matrix,
        profile=profile,
        session_rows=session_rows,
        pathology_v12=pathology_v12,
        pathology_v11=pathology_v11,
        hint_index=hint_index,
        holdout_fraction=args.holdout_fraction,
    )
    report["profile_path"] = str(profile_path.relative_to(ROOT)).replace("\\", "/")
    report["profile_source"] = profile_source
    _assert_no_forbidden(report)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {args.out}")
    print(
        "days:",
        report["n_session_days"],
        "holdout:",
        len(report["holdout_dates"]),
        "consistency_holdout:",
        report["eval_axes"]["orchestration_consistency"]["holdout"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
