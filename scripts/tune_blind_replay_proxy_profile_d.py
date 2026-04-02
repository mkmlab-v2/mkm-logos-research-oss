#!/usr/bin/env python3
"""Tune proxy profile D parameters on BTC/KOSPI blind replay runs."""

from __future__ import annotations

import argparse
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "BLIND_REPLAY_PROXY_PROFILE_D_PARAMS_V1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip().lstrip("\ufeff")
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _norm_label(v: Any) -> str:
    s = str(v or "").strip().upper()
    if s in {"DOWN", "BEAR", "DOWN_STRONG", "NEGATIVE"}:
        return "DOWN_STRONG"
    if s in {"UP", "BULL", "UP_STRONG", "POSITIVE"}:
        return "UP_STRONG"
    if s in {"NEUTRAL", "HOLD", "FLAT"}:
        return "NEUTRAL"
    return "UNKNOWN"


def _sign(score: float, band: float) -> str:
    if score <= -band:
        return "DOWN_STRONG"
    if score >= band:
        return "UP_STRONG"
    return "NEUTRAL"


def _weighted_sigma(values: dict[str, float], weights: dict[str, float]) -> float:
    total_w = sum(weights.values())
    if total_w <= 0:
        return 0.0
    mu = sum(weights[k] * values.get(k, 0.0) for k in weights) / total_w
    var = sum(weights[k] * ((values.get(k, 0.0) - mu) ** 2) for k in weights) / total_w
    return math.sqrt(max(0.0, var))


def _load_seed_runs(grid_path: Path) -> list[tuple[list[dict[str, Any]], dict[str, str]]]:
    grid = _read_json(grid_path)
    best_cfg = grid.get("best_config") if isinstance(grid.get("best_config"), dict) else {}
    runs = best_cfg.get("seed_runs") if isinstance(best_cfg.get("seed_runs"), list) else []
    out: list[tuple[list[dict[str, Any]], dict[str, str]]] = []
    for r in runs:
        pub = Path(str(r.get("public_dataset") or ""))
        key = Path(str(r.get("answer_key") or ""))
        public_rows = _read_jsonl(pub)
        key_rows = _read_jsonl(key)
        if not public_rows or not key_rows:
            continue
        truth = {str(x.get("sample_id") or ""): _norm_label(x.get("answer_label")) for x in key_rows}
        out.append((public_rows, truth))
    return out


def _eval_one_run_bucketed(
    params: dict[str, float], public_rows: list[dict[str, Any]], truth: dict[str, str]
) -> tuple[float, float]:
    vols: list[float] = []
    for r in public_rows:
        feat = r.get("features") if isinstance(r.get("features"), dict) else {}
        vols.append(float(feat.get("volatility_index") or 0.0))
    vol_sorted = sorted(vols)
    med = vol_sorted[len(vol_sorted) // 2] if vol_sorted else 0.0

    def _bal_for_bucket(target_high: bool) -> float:
        per_total = {"DOWN_STRONG": 0, "UP_STRONG": 0, "NEUTRAL": 0}
        per_hit = {"DOWN_STRONG": 0, "UP_STRONG": 0, "NEUTRAL": 0}
        for r in public_rows:
            sid = str(r.get("sample_id") or "")
            t = truth.get(sid, "UNKNOWN")
            if t in per_total:
                feat = r.get("features") if isinstance(r.get("features"), dict) else {}
                vol = float(feat.get("volatility_index") or 0.0)
                is_high = vol >= med
                if is_high != target_high:
                    continue
                per_total[t] += 1
            else:
                continue
            feat = r.get("features") if isinstance(r.get("features"), dict) else {}
            m = float(feat.get("momentum_index") or 0.0)
            v = float(feat.get("volatility_index") or 0.0)
            d = float(feat.get("drawdown_index") or 0.0)
            rp = float(feat.get("range_spread_index") or 0.0)

            sm = (params["m_myeongni"] * m) + (params["d_myeongni"] * d)
            ss = (params["m_sasang"] * m) + (params["d_sasang"] * d) - (params["v_penalty"] * max(0.0, v - 0.12))
            sl = (params["m_logos"] * m) + (params["r_bonus"] * (0.25 - min(0.25, abs(rp - 0.25))))

            vm = _sign(sm, params["band_m"])
            vs = _sign(ss, params["band_s"])
            vl = _sign(sl, params["band_l"])
            down = [vm, vs, vl].count("DOWN_STRONG")
            up = [vm, vs, vl].count("UP_STRONG")
            pred = "DOWN_STRONG" if down > up else ("UP_STRONG" if up > down else "NEUTRAL")
            if pred == t and t in per_hit:
                per_hit[t] += 1
        parts: list[float] = []
        for lbl in ("DOWN_STRONG", "UP_STRONG", "NEUTRAL"):
            if per_total[lbl] > 0:
                parts.append(per_hit[lbl] / per_total[lbl])
        return (sum(parts) / len(parts)) if parts else 0.0

    low_bal = _bal_for_bucket(target_high=False)
    high_bal = _bal_for_bucket(target_high=True)
    return low_bal, high_bal


def _eval_one_run(params: dict[str, float], public_rows: list[dict[str, Any]], truth: dict[str, str]) -> float:
    per_total = {"DOWN_STRONG": 0, "UP_STRONG": 0, "NEUTRAL": 0}
    per_hit = {"DOWN_STRONG": 0, "UP_STRONG": 0, "NEUTRAL": 0}
    for r in public_rows:
        sid = str(r.get("sample_id") or "")
        t = truth.get(sid, "UNKNOWN")
        if t in per_total:
            per_total[t] += 1
        feat = r.get("features") if isinstance(r.get("features"), dict) else {}
        m = float(feat.get("momentum_index") or 0.0)
        v = float(feat.get("volatility_index") or 0.0)
        d = float(feat.get("drawdown_index") or 0.0)
        rp = float(feat.get("range_spread_index") or 0.0)

        sm = (params["m_myeongni"] * m) + (params["d_myeongni"] * d)
        ss = (params["m_sasang"] * m) + (params["d_sasang"] * d) - (params["v_penalty"] * max(0.0, v - 0.12))
        sl = (params["m_logos"] * m) + (params["r_bonus"] * (0.25 - min(0.25, abs(rp - 0.25))))

        vm = _sign(sm, params["band_m"])
        vs = _sign(ss, params["band_s"])
        vl = _sign(sl, params["band_l"])
        down = [vm, vs, vl].count("DOWN_STRONG")
        up = [vm, vs, vl].count("UP_STRONG")
        pred = "DOWN_STRONG" if down > up else ("UP_STRONG" if up > down else "NEUTRAL")
        if pred == t and t in per_hit:
            per_hit[t] += 1

    parts: list[float] = []
    for lbl in ("DOWN_STRONG", "UP_STRONG", "NEUTRAL"):
        if per_total[lbl] > 0:
            parts.append(per_hit[lbl] / per_total[lbl])
    return (sum(parts) / len(parts)) if parts else 0.0


def _sample_params(rng: random.Random) -> dict[str, float]:
    return {
        "m_myeongni": round(rng.uniform(1.3, 3.2), 4),
        "d_myeongni": round(rng.uniform(0.3, 1.3), 4),
        "m_sasang": round(rng.uniform(0.7, 1.7), 4),
        "d_sasang": round(rng.uniform(0.05, 0.55), 4),
        "v_penalty": round(rng.uniform(0.05, 0.35), 4),
        "m_logos": round(rng.uniform(1.0, 2.3), 4),
        "r_bonus": round(rng.uniform(0.05, 0.3), 4),
        "band_m": round(rng.uniform(0.04, 0.11), 4),
        "band_s": round(rng.uniform(0.05, 0.12), 4),
        "band_l": round(rng.uniform(0.05, 0.12), 4),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Tune profile D parameters with unified objective.")
    ap.add_argument("--btc-grid", type=Path, required=True)
    ap.add_argument("--kospi-grid", type=Path, required=True)
    ap.add_argument("--iters", type=int, default=240)
    ap.add_argument("--seed", type=int, default=20260402)
    ap.add_argument("--w-btc", type=float, default=0.7)
    ap.add_argument("--w-kospi", type=float, default=0.3)
    ap.add_argument("--kappa", type=float, default=0.15)
    ap.add_argument(
        "--high-vol-penalty",
        type=float,
        default=0.0,
        help="Additional penalty * max(0, low_bal - high_bal) across assets.",
    )
    ap.add_argument(
        "--kospi-floor",
        type=float,
        default=0.0,
        help="Minimum acceptable KOSPI balanced accuracy before extra penalty.",
    )
    ap.add_argument(
        "--kospi-floor-penalty",
        type=float,
        default=0.0,
        help="Penalty coefficient for max(0, kospi_floor - kospi_bal).",
    )
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    btc_runs = _load_seed_runs(args.btc_grid)
    kospi_runs = _load_seed_runs(args.kospi_grid)
    if not btc_runs or not kospi_runs:
        raise SystemExit("No seed runs loaded from grids")

    rng = random.Random(args.seed)
    top: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    weights = {"BTC": float(args.w_btc), "KOSPI": float(args.w_kospi)}

    for i in range(1, int(args.iters) + 1):
        params = _sample_params(rng)
        btc_bal = sum(_eval_one_run(params, pub, truth) for pub, truth in btc_runs) / len(btc_runs)
        kospi_bal = sum(_eval_one_run(params, pub, truth) for pub, truth in kospi_runs) / len(kospi_runs)
        btc_buckets = [_eval_one_run_bucketed(params, pub, truth) for pub, truth in btc_runs]
        kospi_buckets = [_eval_one_run_bucketed(params, pub, truth) for pub, truth in kospi_runs]
        btc_low_mean = sum(x[0] for x in btc_buckets) / len(btc_buckets)
        btc_high_mean = sum(x[1] for x in btc_buckets) / len(btc_buckets)
        kospi_low_mean = sum(x[0] for x in kospi_buckets) / len(kospi_buckets)
        kospi_high_mean = sum(x[1] for x in kospi_buckets) / len(kospi_buckets)
        low_high_gap_penalty = (
            max(0.0, btc_low_mean - btc_high_mean) + max(0.0, kospi_low_mean - kospi_high_mean)
        ) / 2.0
        kospi_floor_gap_penalty = max(0.0, float(args.kospi_floor) - kospi_bal)
        mu = (weights["BTC"] * btc_bal + weights["KOSPI"] * kospi_bal) / (weights["BTC"] + weights["KOSPI"])
        sigma = _weighted_sigma({"BTC": btc_bal, "KOSPI": kospi_bal}, weights)
        score = (
            mu
            - float(args.kappa) * sigma
            - float(args.high_vol_penalty) * low_high_gap_penalty
            - float(args.kospi_floor_penalty) * kospi_floor_gap_penalty
        )
        row = {
            "iter": i,
            "params": params,
            "btc_balanced_accuracy_mean": round(btc_bal, 6),
            "kospi_balanced_accuracy_mean": round(kospi_bal, 6),
            "btc_low_balanced_accuracy_mean": round(btc_low_mean, 6),
            "btc_high_balanced_accuracy_mean": round(btc_high_mean, 6),
            "kospi_low_balanced_accuracy_mean": round(kospi_low_mean, 6),
            "kospi_high_balanced_accuracy_mean": round(kospi_high_mean, 6),
            "low_high_gap_penalty": round(low_high_gap_penalty, 6),
            "kospi_floor_gap_penalty": round(kospi_floor_gap_penalty, 6),
            "unified_score_balanced": round(score, 6),
            "mu_balanced": round(mu, 6),
            "sigma_balanced": round(sigma, 6),
        }
        if (best is None) or (float(row["unified_score_balanced"]) > float(best["unified_score_balanced"])):
            best = row
        top.append(row)
        top.sort(key=lambda x: float(x["unified_score_balanced"]), reverse=True)
        if len(top) > 20:
            top = top[:20]

    assert best is not None
    payload = {
        "schema": "blind_replay_proxy_profile_d_tuning_v1",
        "generated_at_utc": _utc_now(),
        "exploratory_only": True,
        "a_track_binding_forbidden": True,
        "inputs": {
            "btc_grid": str(args.btc_grid.resolve()),
            "kospi_grid": str(args.kospi_grid.resolve()),
            "btc_seed_runs": len(btc_runs),
            "kospi_seed_runs": len(kospi_runs),
            "iters": int(args.iters),
            "seed": int(args.seed),
        },
        "objective": {
            "w_btc": float(args.w_btc),
            "w_kospi": float(args.w_kospi),
            "kappa": float(args.kappa),
            "high_vol_penalty": float(args.high_vol_penalty),
            "kospi_floor": float(args.kospi_floor),
            "kospi_floor_penalty": float(args.kospi_floor_penalty),
        },
        "best": best,
        "top20": top,
        "note": "Random-search tuning for proxy profile D.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out.resolve()}")
    print(f"BEST unified_score_balanced={best['unified_score_balanced']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

