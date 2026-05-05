#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "exodus_pressure_v1_latest.json"
DEFAULT_SOURCE = ROOT / "docs" / "final" / "artifacts" / "exodus_pressure_source_latest.json"
DEFAULT_MACRO_SMOKE = ROOT / "docs" / "final" / "artifacts" / "macro_risk_warning_api_smoke_latest.json"
DEFAULT_DAILY_CLOSE = ROOT / "docs" / "final" / "artifacts" / "daily_market_close_inputs_latest.json"
DEFAULT_DUAL_LEG = ROOT / "docs" / "final" / "artifacts" / "trackc_prophecy_dual_leg_brief_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return doc if isinstance(doc, dict) else {}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _score_from_source(source: dict[str, Any]) -> tuple[dict[str, float], str]:
    metrics = source.get("metrics") if isinstance(source.get("metrics"), dict) else {}
    if not metrics:
        return {}, "missing_source_metrics"
    required = ("cex_net_outflow_index", "stablecoin_ammo_index", "gold_safe_haven_flow", "dollar_stress_proxy", "risk_off_rotation")
    out: dict[str, float] = {}
    for k in required:
        if k not in metrics:
            return {}, f"missing_metric:{k}"
        out[k] = _clamp(_to_float(metrics.get(k), 50.0), 0.0, 100.0)
    return out, "source_json"


def _score_from_proxy(
    *,
    macro_smoke: dict[str, Any],
    daily_close: dict[str, Any],
    dual_leg: dict[str, Any],
) -> tuple[dict[str, float], str]:
    frag = macro_smoke.get("fragility_composite") if isinstance(macro_smoke.get("fragility_composite"), dict) else {}
    insight = macro_smoke.get("insight_7") if isinstance(macro_smoke.get("insight_7"), dict) else {}

    score_0_100 = _clamp(_to_float(frag.get("score_0_100"), 50.0), 0.0, 100.0)
    tail = _clamp(_to_float(insight.get("tail_event_pressure"), 0.5), 0.0, 1.0)
    funding = _clamp(_to_float(insight.get("funding_pressure_signal"), 0.5), 0.0, 1.0)
    cross = _clamp(_to_float(insight.get("cross_asset_dislocation"), 0.5), 0.0, 1.0)
    policy = _clamp(_to_float(insight.get("macro_policy_shock_risk"), 0.5), 0.0, 1.0)
    crowd = _clamp(_to_float(insight.get("crowd_positioning_fragility"), 0.5), 0.0, 1.0)

    btc_d1 = _to_float(daily_close.get("btc_binance_d1_return_pct"), 0.0)
    kospi_d1 = _to_float(daily_close.get("kospi_d1_return_pct"), 0.0)
    leg_delta = _to_float((dual_leg.get("delta") or {}).get("btc_minus_kospi_hit_rate"), 0.0)

    # Proxy mapping for v1 smoke-friendly operation.
    cex = _clamp(40.0 + (tail * 30.0) + max(-10.0, min(10.0, -btc_d1 * 2.0)), 0.0, 100.0)
    stable = _clamp(45.0 + (funding * 28.0) + max(-8.0, min(8.0, -btc_d1)), 0.0, 100.0)
    gold = _clamp(42.0 + (cross * 24.0) + max(-6.0, min(6.0, score_0_100 * 0.05)), 0.0, 100.0)
    dollar = _clamp(38.0 + (policy * 30.0) + max(-8.0, min(8.0, score_0_100 * 0.04)), 0.0, 100.0)
    rotation = _clamp(35.0 + (crowd * 20.0) + max(-10.0, min(10.0, (kospi_d1 - btc_d1) * 1.5 + leg_delta * 40.0)), 0.0, 100.0)

    return {
        "cex_net_outflow_index": cex,
        "stablecoin_ammo_index": stable,
        "gold_safe_haven_flow": gold,
        "dollar_stress_proxy": dollar,
        "risk_off_rotation": rotation,
    }, "proxy_from_existing_artifacts"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build Exodus Pressure score (X-axis) from 5 factors.")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--source-json", type=Path, default=DEFAULT_SOURCE)
    p.add_argument("--macro-smoke-json", type=Path, default=DEFAULT_MACRO_SMOKE)
    p.add_argument("--daily-close-json", type=Path, default=DEFAULT_DAILY_CLOSE)
    p.add_argument("--dual-leg-json", type=Path, default=DEFAULT_DUAL_LEG)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_path = args.out if args.out.is_absolute() else (ROOT / args.out)
    source_path = args.source_json if args.source_json.is_absolute() else (ROOT / args.source_json)
    macro_path = args.macro_smoke_json if args.macro_smoke_json.is_absolute() else (ROOT / args.macro_smoke_json)
    daily_path = args.daily_close_json if args.daily_close_json.is_absolute() else (ROOT / args.daily_close_json)
    dual_path = args.dual_leg_json if args.dual_leg_json.is_absolute() else (ROOT / args.dual_leg_json)

    source_doc = _read_json(source_path)
    factors, source_mode = _score_from_source(source_doc)
    if not factors:
        factors, source_mode = _score_from_proxy(
            macro_smoke=_read_json(macro_path),
            daily_close=_read_json(daily_path),
            dual_leg=_read_json(dual_path),
        )

    weights = {
        "cex_net_outflow_index": 0.30,
        "stablecoin_ammo_index": 0.25,
        "gold_safe_haven_flow": 0.20,
        "dollar_stress_proxy": 0.15,
        "risk_off_rotation": 0.10,
    }
    score = 0.0
    for k, w in weights.items():
        score += _to_float(factors.get(k), 50.0) * w
    score = _clamp(score, 0.0, 100.0)

    out = {
        "schema": "exodus_pressure_v1",
        "generated_at_utc": _utc_now(),
        "source_mode": source_mode,
        "weights": weights,
        "factor_scores_0_100": {k: round(_to_float(v), 6) for k, v in factors.items()},
        "score_0_100": round(score, 6),
        "note": "X-axis decision-support score. Narrative and investment action remain non-gating.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"exodus_pressure_v1: PASS -> {out_path}")
    print(f"source_mode={source_mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

