#!/usr/bin/env python3
"""SANDBOX: sasang dynamics JSONL vs BTC realized direction (from Phase3 join calendar)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SASANG = (
    ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.calendar_stub_through_202604.jsonl"
)
DEFAULT_JOINED = ROOT / "reports/btrack_phase3_leading_sensors_joined_v1_latest.jsonl"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        if isinstance(o, dict):
            rows.append(o)
    return rows


def _hit_on_rows(rows: list[dict[str, Any]]) -> tuple[int, int, float | None]:
    hits = 0
    n = 0
    for r in rows:
        pd = str(r.get("predicted_direction") or "").strip().lower()
        ad = str(r.get("actual_direction") or "").strip().lower()
        if pd not in ("bull", "bear", "neutral") or ad not in ("bull", "bear", "neutral"):
            continue
        n += 1
        if pd == ad:
            hits += 1
    if n == 0:
        return 0, 0, None
    return hits, n, hits / n


def _date_from_ts(ts: str) -> str:
    return str(ts or "")[:10]


def _sasang_by_date(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        d = _date_from_ts(str(row.get("ts_utc") or ""))
        if d:
            out[d] = row
    return out


def _predict(row: dict[str, Any], strategy: str) -> str:
    if strategy == "mapping_target":
        mt = str(row.get("mapping_target") or "").strip().lower()
        if mt in ("bull", "bear"):
            return mt
        if mt in ("sideways", "neutral"):
            return "neutral"
        return "neutral"
    if strategy == "heat_cold_sign":
        mr = row.get("machine_readables") if isinstance(row.get("machine_readables"), dict) else {}
        try:
            heat = float(mr.get("heat_proxy"))
            cold = float(mr.get("cold_proxy"))
        except (TypeError, ValueError):
            return "neutral"
        if heat > cold:
            return "bull"
        if heat < cold:
            return "bear"
        return "neutral"
    raise ValueError(f"unknown strategy: {strategy}")


def eval_sasang_dynamics(
    joined_jsonl: Path,
    sasang_jsonl: Path,
    *,
    strategy: str,
    recent_trading_days: int = 30,
) -> dict[str, Any]:
    if not joined_jsonl.is_file():
        return {"error": f"missing joined: {joined_jsonl}", "n_evaluated": 0}
    if not sasang_jsonl.is_file():
        return {"error": f"missing sasang jsonl: {sasang_jsonl}", "n_evaluated": 0}

    sasang = _sasang_by_date(sasang_jsonl)
    cal = [
        r
        for r in _read_jsonl(joined_jsonl)
        if str(r.get("instrument") or "btc").strip().lower() == "btc"
    ]
    cal.sort(key=lambda r: str(r.get("eval_date") or ""))
    if recent_trading_days > 0:
        cal = cal[-recent_trading_days:]

    scored: list[dict[str, Any]] = []
    gaps: list[float] = []
    for r in cal:
        d = str(r.get("eval_date") or "")
        srow = sasang.get(d)
        if not srow:
            continue
        pred = _predict(srow, strategy)
        mr = srow.get("machine_readables") if isinstance(srow.get("machine_readables"), dict) else {}
        try:
            gaps.append(abs(float(mr.get("heat_proxy")) - float(mr.get("cold_proxy"))))
        except (TypeError, ValueError):
            pass
        scored.append(
            {
                "eval_date": d,
                "predicted_direction": pred,
                "actual_direction": r.get("actual_direction"),
                "sentiment_polarity_gap": gaps[-1] if gaps else None,
            }
        )

    hits, n, rate = _hit_on_rows(scored)
    gap_mean = sum(gaps) / len(gaps) if gaps else None
    return {
        "price_directional_hit_rate": round(rate, 6) if rate is not None else None,
        "n_evaluated": n,
        "price_hits": hits,
        "alert_1_pass": rate is not None and rate >= 0.5,
        "strategy": strategy,
        "n_scored_rows": len(scored),
        "sentiment_polarity_gap_mean": round(gap_mean, 6) if gap_mean is not None else None,
    }
