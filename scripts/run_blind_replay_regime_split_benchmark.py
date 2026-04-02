#!/usr/bin/env python3
"""Regime-conditional blind replay benchmark (high-vol vs low-vol)."""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "blind_replay_regime_split_benchmark_latest.json"


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


def _sign_from_score(score: float, neutral_band: float) -> str:
    if score <= -neutral_band:
        return "DOWN_STRONG"
    if score >= neutral_band:
        return "UP_STRONG"
    return "NEUTRAL"


def _profile_params(profile: str) -> dict[str, float]:
    p = profile.strip().upper()
    if p == "A":
        return {
            "m_myeongni": 2.6,
            "d_myeongni": 1.0,
            "m_sasang": 1.3,
            "d_sasang": 0.35,
            "v_penalty": 0.22,
            "m_logos": 1.2,
            "r_bonus": 0.10,
            "band_m": 0.08,
            "band_s": 0.10,
            "band_l": 0.09,
        }
    if p == "B":
        return {
            "m_myeongni": 2.2,
            "d_myeongni": 0.8,
            "m_sasang": 1.2,
            "d_sasang": 0.3,
            "v_penalty": 0.2,
            "m_logos": 1.4,
            "r_bonus": 0.15,
            "band_m": 0.07,
            "band_s": 0.09,
            "band_l": 0.08,
        }
    if p == "C":
        return {
            "m_myeongni": 1.8,
            "d_myeongni": 0.6,
            "m_sasang": 1.0,
            "d_sasang": 0.25,
            "v_penalty": 0.15,
            "m_logos": 1.8,
            "r_bonus": 0.22,
            "band_m": 0.06,
            "band_s": 0.08,
            "band_l": 0.07,
        }
    raise ValueError(f"Unknown profile: {profile}")


def _predict(profile: str, feat: dict[str, Any]) -> str:
    params = _profile_params(profile)
    m = float(feat.get("momentum_index") or 0.0)
    v = float(feat.get("volatility_index") or 0.0)
    d = float(feat.get("drawdown_index") or 0.0)
    rp = float(feat.get("range_spread_index") or 0.0)

    score_myeongni = (params["m_myeongni"] * m) + (params["d_myeongni"] * d)
    score_sasang = (params["m_sasang"] * m) + (params["d_sasang"] * d) - (
        params["v_penalty"] * max(0.0, v - 0.12)
    )
    score_logos = (params["m_logos"] * m) + (params["r_bonus"] * (0.25 - min(0.25, abs(rp - 0.25))))

    sign_m = _sign_from_score(score_myeongni, params["band_m"])
    sign_s = _sign_from_score(score_sasang, params["band_s"])
    sign_l = _sign_from_score(score_logos, params["band_l"])

    down = [sign_m, sign_s, sign_l].count("DOWN_STRONG")
    up = [sign_m, sign_s, sign_l].count("UP_STRONG")
    if down > up:
        return "DOWN_STRONG"
    if up > down:
        return "UP_STRONG"
    return "NEUTRAL"


def _bucketize(public_rows: list[dict[str, Any]]) -> dict[str, str]:
    vols: list[float] = []
    for r in public_rows:
        feat = r.get("features") if isinstance(r.get("features"), dict) else {}
        vols.append(float(feat.get("volatility_index") or 0.0))
    if not vols:
        return {}
    med = statistics.median(vols)
    out: dict[str, str] = {}
    for r in public_rows:
        sid = str(r.get("sample_id") or "")
        feat = r.get("features") if isinstance(r.get("features"), dict) else {}
        vol = float(feat.get("volatility_index") or 0.0)
        out[sid] = "HIGH_VOL" if vol >= med else "LOW_VOL"
    return out


def _eval_bucket(
    profile: str,
    public_rows: list[dict[str, Any]],
    key_rows: list[dict[str, Any]],
    bucket_map: dict[str, str],
    bucket_name: str,
) -> dict[str, float]:
    truth = {str(r.get("sample_id") or ""): _norm_label(r.get("answer_label")) for r in key_rows}
    matched = 0
    hit = 0
    per_label_total = {"DOWN_STRONG": 0, "UP_STRONG": 0, "NEUTRAL": 0}
    per_label_hit = {"DOWN_STRONG": 0, "UP_STRONG": 0, "NEUTRAL": 0}

    for r in public_rows:
        sid = str(r.get("sample_id") or "")
        if bucket_map.get(sid) != bucket_name:
            continue
        t = truth.get(sid, "UNKNOWN")
        if t in per_label_total:
            per_label_total[t] += 1
        feat = r.get("features") if isinstance(r.get("features"), dict) else {}
        pred = _predict(profile, feat)
        matched += 1
        if pred == t:
            hit += 1
            if t in per_label_hit:
                per_label_hit[t] += 1

    hit_rate = (hit / matched) if matched else 0.0
    parts: list[float] = []
    for lbl in ("DOWN_STRONG", "UP_STRONG", "NEUTRAL"):
        t = per_label_total[lbl]
        if t > 0:
            parts.append(per_label_hit[lbl] / t)
    bal = (sum(parts) / len(parts)) if parts else 0.0
    return {"matched": float(matched), "hit_rate": hit_rate, "balanced_accuracy": bal}


def _aggregate(vals: list[float]) -> dict[str, float]:
    if not vals:
        return {"mean": 0.0, "std": 0.0}
    mean = sum(vals) / len(vals)
    var = sum((x - mean) ** 2 for x in vals) / len(vals)
    return {"mean": round(mean, 6), "std": round(var**0.5, 6)}


def _run_asset(grid_path: Path, profiles: list[str]) -> dict[str, Any]:
    grid = _read_json(grid_path)
    best_cfg = grid.get("best_config") if isinstance(grid.get("best_config"), dict) else {}
    seed_runs = best_cfg.get("seed_runs") if isinstance(best_cfg.get("seed_runs"), list) else []
    result: dict[str, Any] = {"config_tag": best_cfg.get("config_tag"), "profiles": {}}

    for p in profiles:
        low_hit_vals: list[float] = []
        low_bal_vals: list[float] = []
        high_hit_vals: list[float] = []
        high_bal_vals: list[float] = []
        low_n_vals: list[float] = []
        high_n_vals: list[float] = []
        for run in seed_runs:
            public_path = Path(str(run.get("public_dataset") or ""))
            key_path = Path(str(run.get("answer_key") or ""))
            public_rows = _read_jsonl(public_path)
            key_rows = _read_jsonl(key_path)
            if not public_rows or not key_rows:
                continue
            bucket_map = _bucketize(public_rows)
            low = _eval_bucket(p, public_rows, key_rows, bucket_map, "LOW_VOL")
            high = _eval_bucket(p, public_rows, key_rows, bucket_map, "HIGH_VOL")
            low_hit_vals.append(float(low["hit_rate"]))
            low_bal_vals.append(float(low["balanced_accuracy"]))
            high_hit_vals.append(float(high["hit_rate"]))
            high_bal_vals.append(float(high["balanced_accuracy"]))
            low_n_vals.append(float(low["matched"]))
            high_n_vals.append(float(high["matched"]))

        result["profiles"][p] = {
            "LOW_VOL": {
                "hit_rate": _aggregate(low_hit_vals),
                "balanced_accuracy": _aggregate(low_bal_vals),
                "matched_mean": round((sum(low_n_vals) / len(low_n_vals)) if low_n_vals else 0.0, 3),
            },
            "HIGH_VOL": {
                "hit_rate": _aggregate(high_hit_vals),
                "balanced_accuracy": _aggregate(high_bal_vals),
                "matched_mean": round((sum(high_n_vals) / len(high_n_vals)) if high_n_vals else 0.0, 3),
            },
        }

    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Run regime split benchmark for blind replay grids.")
    ap.add_argument("--btc-grid", type=Path, required=True)
    ap.add_argument("--kospi-grid", type=Path, required=True)
    ap.add_argument("--profiles", default="A,B,C")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    profiles = [p.strip().upper() for p in str(args.profiles).split(",") if p.strip()]
    btc = _run_asset(args.btc_grid, profiles)
    kospi = _run_asset(args.kospi_grid, profiles)

    report = {
        "schema": "blind_replay_regime_split_benchmark_v1",
        "generated_at_utc": _utc_now(),
        "exploratory_only": True,
        "a_track_binding_forbidden": True,
        "inputs": {"btc_grid": str(args.btc_grid.resolve()), "kospi_grid": str(args.kospi_grid.resolve())},
        "bucket_policy": "median(volatility_index): HIGH_VOL >= median else LOW_VOL",
        "profiles": profiles,
        "assets": {"BTC": btc, "KOSPI": kospi},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

