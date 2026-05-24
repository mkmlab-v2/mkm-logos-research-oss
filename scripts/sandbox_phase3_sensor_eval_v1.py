#!/usr/bin/env python3
"""Evaluate Phase3 leading-sensor z-scores vs realized direction (SANDBOX only)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JOINED = ROOT / "reports" / "btrack_phase3_leading_sensors_joined_v1_latest.jsonl"


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


def _z_to_direction(z: float, *, deadband: float = 0.0) -> str:
    if z > deadband:
        return "bull"
    if z < -deadband:
        return "bear"
    return "neutral"


def _extract_z(row: dict[str, Any], sensor_z_key: str) -> float | None:
    if sensor_z_key == "leading_composite_signed_flow_z":
        raw = row.get(sensor_z_key)
    else:
        sensors = row.get("sensors") if isinstance(row.get("sensors"), dict) else {}
        raw = sensors.get(sensor_z_key)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def eval_phase3_sensor(
    joined_jsonl: Path,
    *,
    sensor_z_key: str,
    recent_trading_days: int = 30,
    invert: bool = False,
    deadband: float = 0.0,
    instrument_filter: str = "btc",
) -> dict[str, Any]:
    if not joined_jsonl.is_file():
        return {"error": f"missing joined jsonl: {joined_jsonl}", "n_evaluated": 0}

    raw_rows = _read_jsonl(joined_jsonl)
    if instrument_filter:
        raw_rows = [
            r
            for r in raw_rows
            if str(r.get("instrument") or "btc").strip().lower() == instrument_filter
        ]
    raw_rows.sort(key=lambda r: str(r.get("eval_date") or ""))
    if recent_trading_days > 0:
        raw_rows = raw_rows[-recent_trading_days:]

    scored: list[dict[str, Any]] = []
    for r in raw_rows:
        z = _extract_z(r, sensor_z_key)
        if z is None:
            continue
        pred = _z_to_direction(z, deadband=deadband)
        if invert and pred in ("bull", "bear"):
            pred = "bear" if pred == "bull" else "bull"
        scored.append(
            {
                "eval_date": r.get("eval_date"),
                "predicted_direction": pred,
                "actual_direction": r.get("actual_direction"),
                "sensor_z": z,
            }
        )

    hits, n, rate = _hit_on_rows(scored)
    return {
        "price_directional_hit_rate": round(rate, 6) if rate is not None else None,
        "n_evaluated": n,
        "price_hits": hits,
        "alert_1_pass": rate is not None and rate >= 0.5,
        "sensor_z_key": sensor_z_key,
        "n_scored_rows": len(scored),
        "invert": invert,
        "deadband": deadband,
    }
