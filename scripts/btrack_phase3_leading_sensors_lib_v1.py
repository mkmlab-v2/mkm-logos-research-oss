"""Shared Phase 3 leading-sensor ablation helpers (research_only)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(ROOT))
from scripts.eval_prophecy_hit_rate_v1 import _hit_on_directional_calls_only, _hit_on_rows  # noqa: E402

ALERT1 = 0.5


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        if isinstance(o, dict):
            rows.append(o)
    return rows


def sensor_opposes(pred: str, composite: float | None, *, threshold: float) -> bool:
    if composite is None:
        return False
    p = pred.strip().lower()
    if p == "bull":
        return composite < -threshold
    if p == "bear":
        return composite > threshold
    return False


def rows_for_shield(rows: list[dict[str, Any]], *, threshold: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        pred = str(r.get("predicted_direction") or "")
        actual = str(r.get("actual_direction") or "")
        comp = r.get("leading_composite_signed_flow_z")
        comp_f = float(comp) if isinstance(comp, (int, float)) else None
        eff_pred = pred
        if _sensor_opposes_shield(pred, comp_f, threshold=threshold):
            eff_pred = "neutral"
        out.append(
            {
                "eval_date": r.get("eval_date"),
                "instrument": r.get("instrument"),
                "predicted_direction": eff_pred,
                "actual_direction": actual,
                "leading_composite_signed_flow_z": comp_f,
            }
        )
    return out


def _sensor_opposes_shield(pred: str, composite: float | None, *, threshold: float) -> bool:
    return sensor_opposes(pred, composite, threshold=threshold)


def rows_baseline(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "eval_date": r.get("eval_date"),
                "instrument": r.get("instrument"),
                "predicted_direction": r.get("predicted_direction"),
                "actual_direction": r.get("actual_direction"),
                "leading_composite_signed_flow_z": r.get("leading_composite_signed_flow_z"),
            }
        )
    return out


def hit_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    hits, n, rate = _hit_on_rows(rows)
    ch, nc, nn, cr = _hit_on_directional_calls_only(rows)
    return {
        "price_directional_hit_rate": round(rate, 6) if rate is not None else None,
        "n_evaluated": n,
        "price_hits": hits,
        "price_hit_rate_on_directional_calls": round(cr, 6) if cr is not None else None,
        "n_directional_calls": nc,
        "directional_call_hits": ch,
        "n_neutral_predictions": nn,
        "alert_1_pass": rate is not None and rate >= ALERT1,
    }


def overheat_score(composite: float | None) -> float | None:
    if composite is None:
        return None
    return min(1.0, abs(float(composite)))


def size_multiplier_from_overheat(overheat: float | None, *, max_dampen: float = 0.5) -> float:
    """1.0 = full size; lower when market micro overheated (aux only, not direction)."""
    if overheat is None:
        return 1.0
    dampen = min(max_dampen, float(overheat))
    return round(max(1.0 - max_dampen, 1.0 - dampen), 6)


def directional_call_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        pd = str(r.get("predicted_direction") or "").strip().lower()
        if pd in ("bull", "bear"):
            out.append(r)
    return out


def tercile_buckets(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Directional-call hit rate by composite |z| tercile (aux observation)."""
    calls = []
    for r in directional_call_rows(rows):
        comp = r.get("leading_composite_signed_flow_z")
        if comp is None:
            continue
        calls.append(
            {
                "predicted_direction": r.get("predicted_direction"),
                "actual_direction": r.get("actual_direction"),
                "abs_z": abs(float(comp)),
            }
        )
    if len(calls) < 6:
        return {"status": "insufficient", "n": len(calls)}
    calls.sort(key=lambda x: x["abs_z"])
    n = len(calls)
    i1 = n // 3
    i2 = 2 * n // 3
    buckets = {
        "low": calls[:i1],
        "mid": calls[i1:i2],
        "high": calls[i2:],
    }
    out: dict[str, Any] = {}
    for name, sub in buckets.items():
        if not sub:
            out[name] = {"n": 0, "directional_hit_rate": None}
            continue
        shaped = [
            {"predicted_direction": x["predicted_direction"], "actual_direction": x["actual_direction"]}
            for x in sub
        ]
        _, nc, _, cr = _hit_on_directional_calls_only(shaped)
        out[name] = {
            "n": nc,
            "directional_hit_rate": round(cr, 6) if cr is not None else None,
            "abs_z_max": max(x["abs_z"] for x in sub),
        }
    return {"status": "ok", "n_directional_calls": n, "buckets": out}
