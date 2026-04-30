#!/usr/bin/env python3
"""B-track protocol runner for Sasang 4-agent collision architecture.

This script is research-only and builds a deterministic benchmark artifact for:
  - intentional bias injection (4 agents)
  - consensus conflict metric (topological variance)
  - asymmetric veto policy (defense-first hold)
  - regime-window MDD comparison vs baseline
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class Tick:
    t: int
    regime: str
    ret: float
    momentum: float
    similarity: float
    shock: float


def _max_drawdown(equity: list[float]) -> float:
    peak = equity[0] if equity else 1.0
    mdd = 0.0
    for v in equity:
        if v > peak:
            peak = v
        dd = 0.0 if peak <= 0 else (peak - v) / peak
        if dd > mdd:
            mdd = dd
    return mdd


def _equity_curve(returns: list[float]) -> list[float]:
    eq = [1.0]
    for r in returns:
        eq.append(eq[-1] * (1.0 + r))
    return eq


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _variance(xs: list[float]) -> float:
    if not xs:
        return 0.0
    m = _mean(xs)
    return sum((x - m) ** 2 for x in xs) / len(xs)


def _synthetic_ticks(seed: int, n: int) -> list[Tick]:
    rng = random.Random(seed)
    ticks: list[Tick] = []
    momentum = 0.0
    regimes = [
        ("pre_stress", 0.0007, 0.008),
        ("pandemic_crash", -0.0024, 0.023),
        ("recovery", 0.0014, 0.012),
        ("rate_hike", -0.0006, 0.016),
        ("sideways", 0.0002, 0.009),
    ]
    seg = max(1, n // len(regimes))
    t = 0
    for idx, (name, drift, vol) in enumerate(regimes):
        stop = n if idx == len(regimes) - 1 else min(n, (idx + 1) * seg)
        while t < stop:
            base = drift + rng.gauss(0.0, vol)
            shock = abs(base) * (1.0 + 0.4 * rng.random())
            momentum = 0.84 * momentum + 0.16 * base
            # Similarity rises when volatility is low and trend is coherent.
            similarity = max(0.0, min(1.0, 0.65 - (vol * 8.0) + abs(momentum) * 20.0 + rng.gauss(0.0, 0.05)))
            ticks.append(Tick(t=t, regime=name, ret=base, momentum=momentum, similarity=similarity, shock=shock))
            t += 1
    return ticks[:n]


def _regime_from_year(year: int) -> str:
    if year <= 2020:
        return "pandemic_crash"
    if year == 2021:
        return "recovery"
    if year == 2022:
        return "rate_hike"
    if year >= 2025:
        return "sideways"
    return "pre_stress"


def _real_slice_ticks_from_backtest(path: Path, seed: int, fallback_n: int) -> list[Tick]:
    if not path.exists():
        return _synthetic_ticks(seed=seed, n=fallback_n)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return _synthetic_ticks(seed=seed, n=fallback_n)
    regime_switch = doc.get("regime_switch") if isinstance(doc.get("regime_switch"), dict) else {}
    per_year = regime_switch.get("per_year") if isinstance(regime_switch.get("per_year"), list) else []
    if not per_year:
        return _synthetic_ticks(seed=seed, n=fallback_n)

    rng = random.Random(seed + 101)
    ticks: list[Tick] = []
    t = 0
    for row in per_year:
        if not isinstance(row, dict):
            continue
        year = int(row.get("year") or 0)
        m = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
        sample_count = int(m.get("sample_count") or 0)
        if sample_count <= 0:
            continue
        avg_trade_return_pct = float(m.get("avg_trade_return_pct") or 0.0)
        win_rate = float(m.get("win_rate") or 0.5)
        max_dd_pct = float(m.get("max_drawdown_pct") or 5.0)

        mu = avg_trade_return_pct / 100.0
        # Infer rough volatility scale from drawdown and win-rate imbalance.
        sigma = max(0.003, min(0.06, (max_dd_pct / 100.0) / 7.0 + abs(win_rate - 0.5) * 0.02))
        momentum = 0.0
        regime = _regime_from_year(year)
        for _ in range(sample_count):
            base = mu + rng.gauss(0.0, sigma)
            momentum = 0.86 * momentum + 0.14 * base
            similarity = max(0.0, min(1.0, 0.6 + (win_rate - 0.5) * 0.7 - sigma * 4.0 + rng.gauss(0.0, 0.05)))
            shock = abs(base) * (1.0 + 0.5 * rng.random())
            ticks.append(Tick(t=t, regime=regime, ret=base, momentum=momentum, similarity=similarity, shock=shock))
            t += 1
    return ticks if ticks else _synthetic_ticks(seed=seed, n=fallback_n)


def _regime_by_return_context(ret: float, abs_ret: float, q90_abs: float, momentum: float) -> str:
    if abs_ret >= q90_abs and ret < 0:
        return "pandemic_crash"
    if momentum < -0.0012:
        return "rate_hike"
    if momentum > 0.0012:
        return "recovery"
    if abs(momentum) < 0.00045:
        return "sideways"
    return "pre_stress"


def _ticks_from_timeseries_file(path: Path, seed: int) -> list[Tick]:
    if not path.exists():
        return []
    rows: list[tuple[int, float]] = []
    ext = path.suffix.lower()
    try:
        if ext == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                for i, row in enumerate(reader):
                    close_raw = row.get("close") or row.get("Close") or row.get("adj_close") or row.get("Adj Close")
                    if close_raw is None:
                        continue
                    try:
                        close = float(close_raw)
                    except Exception:
                        continue
                    if close <= 0:
                        continue
                    rows.append((i, close))
        else:
            with path.open("r", encoding="utf-8-sig") as fh:
                for i, line in enumerate(fh):
                    s = line.strip()
                    if not s:
                        continue
                    obj = json.loads(s)
                    if not isinstance(obj, dict):
                        continue
                    close_raw = obj.get("close") or obj.get("Close") or obj.get("adj_close")
                    if close_raw is None:
                        continue
                    close = float(close_raw)
                    if close <= 0:
                        continue
                    rows.append((i, close))
    except Exception:
        return []

    if len(rows) < 40:
        return []
    rng = random.Random(seed + 313)
    returns: list[float] = []
    for idx in range(1, len(rows)):
        prev = rows[idx - 1][1]
        cur = rows[idx][1]
        if prev <= 0:
            continue
        returns.append((cur / prev) - 1.0)
    if len(returns) < 30:
        return []
    abs_sorted = sorted(abs(r) for r in returns)
    q90_abs = abs_sorted[int(0.9 * (len(abs_sorted) - 1))]
    ticks: list[Tick] = []
    momentum = 0.0
    for t, r in enumerate(returns):
        momentum = 0.86 * momentum + 0.14 * r
        abs_r = abs(r)
        similarity = max(0.0, min(1.0, 0.7 - abs_r * 15.0 + abs(momentum) * 45.0 + rng.gauss(0.0, 0.04)))
        shock = abs_r * (1.0 + 0.35 * rng.random())
        regime = _regime_by_return_context(ret=r, abs_ret=abs_r, q90_abs=q90_abs, momentum=momentum)
        ticks.append(Tick(t=t, regime=regime, ret=r, momentum=momentum, similarity=similarity, shock=shock))
    return ticks


def _agent_scores(t: Tick, macro_window: float, mom_weight: float, sim_thr: float, defense_lambda: float) -> dict[str, float]:
    # Taeyang: macro/exploration (less penalty on short-term noise)
    taeyang = 0.55 * math.tanh((t.momentum * 220.0) + macro_window) + 0.45 * math.tanh(t.ret * 90.0)
    # Soyang: momentum breakout
    soyang = math.tanh((t.momentum * 320.0 * mom_weight) + (t.ret * 30.0))
    # Taeeum: accumulation/pattern-match (activates only near similarity gate)
    taeeum = math.tanh(((t.similarity - sim_thr) * 12.0) + (t.momentum * 55.0))
    # Soeum: defense (risk-averse, opposite to shock)
    soeum = -math.tanh(defense_lambda * t.shock * 35.0)
    return {"taeyang": taeyang, "soyang": soyang, "taeeum": taeeum, "soeum": soeum}


def _run_protocol(
    ticks: list[Tick],
    macro_window: float,
    mom_weight: float,
    sim_thr: float,
    defense_lambda: float,
    soeum_veto_threshold: float,
) -> dict[str, Any]:
    baseline_returns: list[float] = []
    model_returns: list[float] = []
    topo_variances: list[float] = []
    hold_count = 0
    regime_topo: dict[str, list[float]] = {}

    for t in ticks:
        s = _agent_scores(
            t=t,
            macro_window=macro_window,
            mom_weight=mom_weight,
            sim_thr=sim_thr,
            defense_lambda=defense_lambda,
        )
        votes = [s["taeyang"], s["soyang"], s["taeeum"], s["soeum"]]
        topo = _variance(votes)
        topo_variances.append(topo)
        regime_topo.setdefault(t.regime, []).append(topo)

        # Baseline: single momentum-like policy.
        base_pos = 1.0 if s["soyang"] > 0 else -1.0
        baseline_returns.append(base_pos * t.ret)

        # Asymmetric veto: defensive signal can force HOLD.
        if s["soeum"] < soeum_veto_threshold:
            model_returns.append(0.0)
            hold_count += 1
            continue

        # Otherwise weighted consensus.
        mix = (0.35 * s["taeyang"]) + (0.3 * s["soyang"]) + (0.25 * s["taeeum"]) + (0.1 * s["soeum"])
        pos = 1.0 if mix >= 0 else -1.0
        model_returns.append(pos * t.ret)

    eq_baseline = _equity_curve(baseline_returns)
    eq_model = _equity_curve(model_returns)
    mdd_baseline = _max_drawdown(eq_baseline)
    mdd_model = _max_drawdown(eq_model)
    mdd_delta = mdd_baseline - mdd_model

    regime_topo_mean = {k: _mean(v) for k, v in regime_topo.items()}
    return {
        "baseline_returns": baseline_returns,
        "model_returns": model_returns,
        "metrics": {
            "topological_variance_mean": _mean(topo_variances),
            "topological_variance_p95": sorted(topo_variances)[int(0.95 * (len(topo_variances) - 1))] if topo_variances else 0.0,
            "hold_ratio": (hold_count / len(ticks)) if ticks else 0.0,
            "mdd_baseline": mdd_baseline,
            "mdd_model": mdd_model,
            "mdd_reduction_abs": mdd_delta,
            "mdd_reduction_pct_of_baseline": (mdd_delta / mdd_baseline) if mdd_baseline > 0 else 0.0,
            "regime_topological_variance_mean": regime_topo_mean,
        },
    }


def _bootstrap_p_value(
    baseline_returns: list[float],
    model_returns: list[float],
    observed_delta: float,
    trials: int,
    seed: int,
) -> float:
    rng = random.Random(seed + 7919)
    if not baseline_returns or len(baseline_returns) != len(model_returns):
        return 1.0
    n = len(baseline_returns)
    ge = 0
    for _ in range(trials):
        sample_base = [baseline_returns[rng.randrange(n)] for _ in range(n)]
        sample_model = [model_returns[rng.randrange(n)] for _ in range(n)]
        mdd_b = _max_drawdown(_equity_curve(sample_base))
        mdd_m = _max_drawdown(_equity_curve(sample_model))
        delta = mdd_b - mdd_m
        if delta >= observed_delta:
            ge += 1
    return ge / max(1, trials)


def _paired_permutation_p_value(
    baseline_returns: list[float],
    model_returns: list[float],
    observed_delta: float,
    trials: int,
    seed: int,
) -> float:
    """Permutation p-value under paired null via random sign/swap."""
    rng = random.Random(seed + 1543)
    if not baseline_returns or len(baseline_returns) != len(model_returns):
        return 1.0
    n = len(baseline_returns)
    ge = 0
    for _ in range(trials):
        perm_base: list[float] = []
        perm_model: list[float] = []
        for i in range(n):
            b = baseline_returns[i]
            m = model_returns[i]
            if rng.random() < 0.5:
                perm_base.append(b)
                perm_model.append(m)
            else:
                perm_base.append(m)
                perm_model.append(b)
        mdd_b = _max_drawdown(_equity_curve(perm_base))
        mdd_m = _max_drawdown(_equity_curve(perm_model))
        delta = mdd_b - mdd_m
        if delta >= observed_delta:
            ge += 1
    return ge / max(1, trials)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    default_out = root / "docs" / "final" / "artifacts" / "sasang_4agent_collision_btrack_protocol_latest.json"

    ap = argparse.ArgumentParser(description="Run sasang 4-agent collision B-track protocol.")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--ticks", type=int, default=1200)
    ap.add_argument("--macro-window", type=float, default=0.18)
    ap.add_argument("--mom-weight", type=float, default=0.9)
    ap.add_argument("--similarity-threshold", type=float, default=0.95)
    ap.add_argument("--defense-lambda", type=float, default=4.0)
    ap.add_argument("--soeum-veto-threshold", type=float, default=-0.58)
    ap.add_argument("--bootstrap-trials", type=int, default=400)
    ap.add_argument(
        "--real-backtest-json",
        type=Path,
        default=root / "docs" / "final" / "artifacts" / "btc_time_machine_regime_switch_backtest_latest.json",
    )
    ap.add_argument(
        "--timeseries-file",
        type=Path,
        default=root / "reports" / "constitution" / "btrack_pilot" / "blind_replay" / "kospi_proxy_ohlcv_from_training_result.csv",
    )
    ap.add_argument("--use-real-slice", action="store_true")
    ap.add_argument("--use-timeseries-file", action="store_true")
    ap.add_argument("--out-json", type=Path, default=default_out)
    args = ap.parse_args()

    if args.use_timeseries_file:
        ticks = _ticks_from_timeseries_file(path=args.timeseries_file, seed=args.seed)
        if not ticks:
            ticks = _synthetic_ticks(seed=args.seed, n=max(200, args.ticks))
    elif args.use_real_slice:
        ticks = _real_slice_ticks_from_backtest(path=args.real_backtest_json, seed=args.seed, fallback_n=max(200, args.ticks))
    else:
        ticks = _synthetic_ticks(seed=args.seed, n=max(200, args.ticks))
    run = _run_protocol(
        ticks=ticks,
        macro_window=args.macro_window,
        mom_weight=args.mom_weight,
        sim_thr=args.similarity_threshold,
        defense_lambda=args.defense_lambda,
        soeum_veto_threshold=args.soeum_veto_threshold,
    )
    p_value = _bootstrap_p_value(
        baseline_returns=run["baseline_returns"],
        model_returns=run["model_returns"],
        observed_delta=float(run["metrics"]["mdd_reduction_abs"]),
        trials=max(100, args.bootstrap_trials),
        seed=args.seed,
    )
    p_value_perm = _paired_permutation_p_value(
        baseline_returns=run["baseline_returns"],
        model_returns=run["model_returns"],
        observed_delta=float(run["metrics"]["mdd_reduction_abs"]),
        trials=max(100, args.bootstrap_trials),
        seed=args.seed,
    )

    payload = {
        "schema": "sasang_4agent_collision_btrack_protocol_v1",
        "generated_at_utc": _now_utc(),
        "mode": "research_only",
        "policy_label": "NON_GATING",
        "architecture": {
            "absolute_balance_mode": True,
            "is_fifth_constitution": False,
            "agents": ["taeyang_macro", "soyang_momentum", "taeeum_accumulation", "soeum_defense_veto"],
        },
        "bias_injection": {
            "macro_window": args.macro_window,
            "mom_weight": args.mom_weight,
            "similarity_threshold": args.similarity_threshold,
            "defense_lambda": args.defense_lambda,
            "soeum_veto_threshold": args.soeum_veto_threshold,
        },
        "experiment": {
            "seed": args.seed,
            "ticks": len(ticks),
            "bootstrap_trials": max(100, args.bootstrap_trials),
            "data_mode": (
                "timeseries_file_adapter"
                if args.use_timeseries_file
                else ("real_slice_backtest_adapter" if args.use_real_slice else "synthetic")
            ),
            "real_backtest_json": str(args.real_backtest_json).replace("\\", "/") if args.use_real_slice else None,
            "timeseries_file": str(args.timeseries_file).replace("\\", "/") if args.use_timeseries_file else None,
            "baseline": "single_momentum_policy",
            "candidate": "4agent_collision_with_asymmetric_veto",
        },
        "results": {
            **run["metrics"],
            "mdd_reduction_p_value_bootstrap": p_value,
            "mdd_reduction_p_value_permutation": p_value_perm,
            "statistical_significance_pass_p_lt_0_05": bool((p_value < 0.05) or (p_value_perm < 0.05)),
            "sample_size_warning_low_ticks": bool(len(ticks) < 300),
        },
        "promotion_gate_hint": {
            "decision": (
                "GO_CANDIDATE"
                if (
                    run["metrics"]["mdd_reduction_abs"] > 0
                    and ((p_value < 0.05) or (p_value_perm < 0.05))
                    and len(ticks) >= 300
                )
                else "HOLD"
            ),
            "notes": [
                "B-track evidence only. Do not auto-bridge to Track A.",
                "Use live/real historical slices before any commercialization claim.",
                "If ticks < 300, treat result as directional probe only.",
            ],
        },
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

