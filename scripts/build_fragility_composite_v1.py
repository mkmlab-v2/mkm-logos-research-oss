#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.9, L:0.8, K:0.8, M:0.4}
# Balance: 91
# Purpose: Compute Fact-Lock Fragility Composite v1 macro risk gate.
# Keywords: fragility, macro risk, zscore, regime gate, fact-lock

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "macro_fragility_inputs_latest.json"
DEFAULT_OUTPUT = ROOT / "docs" / "final" / "artifacts" / "fragility_composite_v1_latest.json"
DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "fragility_quaternion_threshold_policy_v1.json"


@dataclass(frozen=True)
class IndicatorSpec:
    name: str
    weight: float


INDICATORS = (
    IndicatorSpec(name="move", weight=0.35),
    IndicatorSpec(name="hy_oas", weight=0.30),
    IndicatorSpec(name="vix", weight=0.20),
    IndicatorSpec(name="dxy_vol", weight=0.15),
)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    if not isinstance(doc, dict):
        return {}
    return doc


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _get_num(source: dict[str, Any], key: str, default: float) -> float:
    raw = source.get(key, default)
    try:
        return float(raw)
    except Exception:
        return float(default)


def _compute_robust_z(x: float, median: float, mad: float) -> tuple[float, bool]:
    if mad <= 0.0:
        return 0.0, False
    scale = 1.4826 * mad
    if scale <= 0.0:
        return 0.0, False
    return _clamp((x - median) / scale, -3.0, 3.0), True


def _base_gate(score: float) -> str:
    if score >= 70.0:
        return "RED"
    if score >= 58.0:
        return "AMBER"
    return "GREEN"


def _state_4d_from_z(z_scores: dict[str, float]) -> dict[str, float]:
    return {
        "stress": _clamp(abs(_to_float(z_scores.get("move"), 0.0)) / 3.0, 0.0, 1.0),
        "liquidity": _clamp(abs(_to_float(z_scores.get("vix"), 0.0)) / 3.0, 0.0, 1.0),
        "credit": _clamp(abs(_to_float(z_scores.get("hy_oas"), 0.0)) / 3.0, 0.0, 1.0),
        "currency": _clamp(abs(_to_float(z_scores.get("dxy_vol"), 0.0)) / 3.0, 0.0, 1.0),
    }


def _quat_delta(curr: dict[str, float], prev: dict[str, float]) -> tuple[float, str]:
    keys = ("stress", "liquidity", "credit", "currency")
    sq = 0.0
    for k in keys:
        sq += (_to_float(curr.get(k), 0.0) - _to_float(prev.get(k), 0.0)) ** 2
    mag = sq**0.5
    if mag >= 0.55:
        label = "phase_shift_high"
    elif mag >= 0.30:
        label = "phase_shift_mid"
    else:
        label = "phase_shift_low"
    return mag, label


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = _clamp(q, 0.0, 1.0) * (len(sorted_values) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = pos - lo
    return sorted_values[lo] * (1.0 - frac) + sorted_values[hi] * frac


def _load_policy(path: Path) -> dict[str, Any]:
    doc = _load_json(path)
    if not doc:
        return {}
    return doc


def _dynamic_quat_label(magnitude: float, history: list[float], policy: dict[str, Any] | None = None) -> tuple[str, dict[str, float]]:
    hist = [max(0.0, _to_float(x, 0.0)) for x in history if _to_float(x, -1.0) >= 0.0]
    hist_sorted = sorted(hist)
    p = policy or {}
    min_count = int(_to_float(p.get("rolling_min_history_count"), 8))
    q_low = _to_float(p.get("rolling_quantile_low"), 0.6)
    q_high = _to_float(p.get("rolling_quantile_high"), 0.85)
    fallback_low = _to_float(p.get("fallback_low_cut"), 0.30)
    fallback_high = _to_float(p.get("fallback_high_cut"), 0.55)
    min_band_gap = _to_float(p.get("min_band_gap"), 0.05)

    if len(hist_sorted) < max(1, min_count):
        low_cut = fallback_low
        high_cut = fallback_high
        mode = "fallback_fixed"
    else:
        low_cut = _quantile(hist_sorted, q_low)
        high_cut = _quantile(hist_sorted, q_high)
        # guardrail to avoid collapsed bands.
        high_cut = max(high_cut, low_cut + min_band_gap)
        mode = "rolling_quantile"
    if magnitude >= high_cut:
        label = "phase_shift_high"
    elif magnitude >= low_cut:
        label = "phase_shift_mid"
    else:
        label = "phase_shift_low"
    return label, {
        "low_cut": round(low_cut, 6),
        "high_cut": round(high_cut, 6),
        "mode": mode,
        "rolling_min_history_count": max(1, min_count),
        "rolling_quantile_low": round(q_low, 6),
        "rolling_quantile_high": round(q_high, 6),
        "min_band_gap": round(min_band_gap, 6),
    }


def _build_default_input() -> dict[str, Any]:
    return {
        "as_of_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "metrics": {
            "move": 126.0,
            "vix": 18.5,
            "hy_oas": 3.9,
            "dxy_vol": 0.118,
        },
        "baselines": {
            "move": {"median_156w": 112.0, "mad_156w": 8.0},
            "vix": {"median_156w": 17.2, "mad_156w": 2.2},
            "hy_oas": {"median_156w": 3.7, "mad_156w": 0.35},
            "dxy_vol": {"median_156w": 0.104, "mad_156w": 0.012},
        },
        "aux": {
            "hy_oas_4w_change_pct": 6.0,
            "hy_oas_4w_change_pct_p85": 9.5,
        },
        "state_memory": {
            "red_active": False,
            "below66_streak": 0,
            "recent_gates": ["GREEN", "AMBER", "AMBER"],
            "red_streak": 0,
        },
        "prev_state_4d": {
            "stress": 0.20,
            "liquidity": 0.18,
            "credit": 0.16,
            "currency": 0.14,
        },
    }


def evaluate_fragility(input_doc: dict[str, Any], policy_doc: dict[str, Any] | None = None) -> dict[str, Any]:
    has_external_input = bool(input_doc)
    doc = input_doc if has_external_input else _build_default_input()

    metrics = doc.get("metrics") if isinstance(doc.get("metrics"), dict) else {}
    baselines = doc.get("baselines") if isinstance(doc.get("baselines"), dict) else {}
    aux = doc.get("aux") if isinstance(doc.get("aux"), dict) else {}
    state_memory = doc.get("state_memory") if isinstance(doc.get("state_memory"), dict) else {}
    prev_state_4d = doc.get("prev_state_4d") if isinstance(doc.get("prev_state_4d"), dict) else {}
    quaternion_history = doc.get("quaternion_history") if isinstance(doc.get("quaternion_history"), list) else []

    z_scores: dict[str, float] = {}
    valid_map: dict[str, bool] = {}
    weighted_sum = 0.0
    all_valid = True

    for spec in INDICATORS:
        metric = _get_num(metrics, spec.name, 0.0)
        baseline = baselines.get(spec.name) if isinstance(baselines.get(spec.name), dict) else {}
        median = _get_num(baseline, "median_156w", metric)
        mad = _get_num(baseline, "mad_156w", 0.0)
        z, ok = _compute_robust_z(metric, median, mad)
        z_scores[spec.name] = z
        valid_map[spec.name] = ok
        weighted_sum += spec.weight * z
        if not ok:
            all_valid = False

    hy_oas_delta = _get_num(aux, "hy_oas_4w_change_pct", 0.0)
    hy_oas_p85 = _get_num(aux, "hy_oas_4w_change_pct_p85", 9999.0)
    hard_trigger_a = z_scores["move"] >= 2.2 and z_scores["hy_oas"] >= 1.8
    hard_trigger_b = hy_oas_delta >= hy_oas_p85 and z_scores["vix"] >= 1.5
    hard_trigger = hard_trigger_a or hard_trigger_b

    score_raw = weighted_sum
    score = _clamp(50.0 + 12.5 * score_raw, 0.0, 100.0)
    base_gate = _base_gate(score)

    red_active_prev = bool(state_memory.get("red_active", False))
    below66_streak_prev = int(state_memory.get("below66_streak", 0) or 0)
    red_streak_prev = int(state_memory.get("red_streak", 0) or 0)
    recent_gates_prev = state_memory.get("recent_gates", [])
    if not isinstance(recent_gates_prev, list):
        recent_gates_prev = []
    recent_gates_prev = [str(x).upper() for x in recent_gates_prev][-3:]

    if not all_valid:
        gate = "NO_SCORE"
        red_active = red_active_prev
        below66_streak = below66_streak_prev
        red_streak = red_streak_prev
        hysteresis_hold = False
    else:
        gate = "RED" if (hard_trigger or base_gate == "RED") else base_gate
        red_active = red_active_prev
        below66_streak = below66_streak_prev
        hysteresis_hold = False

        if red_active_prev and gate != "RED":
            if score < 66.0:
                below66_streak = below66_streak_prev + 1
            else:
                below66_streak = 0
            if below66_streak < 2:
                gate = "RED"
                hysteresis_hold = True
            else:
                red_active = False
                below66_streak = 0
        elif gate == "RED":
            red_active = True
            below66_streak = 0
        else:
            below66_streak = 0

        red_streak = red_streak_prev + 1 if gate == "RED" else 0

    recent_gates = (recent_gates_prev + [gate])[-4:]
    amber_or_red_count = sum(1 for g in recent_gates if g in {"AMBER", "RED"})
    fragility_cluster = amber_or_red_count >= 3
    stress_persistence = red_streak >= 3
    state_4d = _state_4d_from_z(z_scores)
    delta_mag, _delta_label_fixed = _quat_delta(state_4d, prev_state_4d)
    dyn_label, dyn_thresholds = _dynamic_quat_label(delta_mag, quaternion_history, policy_doc)
    history_next = ([_to_float(x, 0.0) for x in quaternion_history] + [delta_mag])[-60:]

    return {
        "schema": "fragility_composite_v1",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "as_of_utc": str(doc.get("as_of_utc", "")),
        "input_status": "external_input" if has_external_input else "fallback_demo_input",
        "weights": {spec.name: spec.weight for spec in INDICATORS},
        "z_scores": z_scores,
        "validity": {"all_valid": all_valid, "per_indicator": valid_map},
        "score": {"raw": round(score_raw, 6), "scaled_0_100": round(score, 4)},
        "gate": gate,
        "gate_details": {
            "base_gate": base_gate if all_valid else "NO_SCORE",
            "hard_trigger": hard_trigger,
            "hard_trigger_a_move_hy": hard_trigger_a,
            "hard_trigger_b_hy_delta_vix": hard_trigger_b,
            "hysteresis_hold_red": hysteresis_hold,
            "fragility_cluster": fragility_cluster,
            "stress_persistence": stress_persistence,
            "hy_oas_4w_change_pct": hy_oas_delta,
            "hy_oas_4w_change_pct_p85": hy_oas_p85,
        },
        "state_4d": {k: round(v, 6) for k, v in state_4d.items()},
        "quaternion_delta": {
            "magnitude": round(delta_mag, 6),
            "label": dyn_label,
            "thresholds": dyn_thresholds,
            "prev_state_available": bool(prev_state_4d),
        },
        "state_memory_next": {
            "red_active": red_active,
            "below66_streak": below66_streak,
            "recent_gates": recent_gates,
            "red_streak": red_streak,
            "state_4d": {k: round(v, 6) for k, v in state_4d.items()},
            "quaternion_history": [round(x, 6) for x in history_next],
        },
        "policy": {
            "sequence": ["DATA", "GATE", "NARRATIVE"],
            "narrative_non_gating_only": True,
            "quaternion_threshold_policy": str((policy_doc or {}).get("schema", "fragility_quaternion_threshold_policy_v1")),
        },
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build Fragility Composite v1 output JSON.")
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input if args.input.is_absolute() else (ROOT / args.input)
    out_path = args.out if args.out.is_absolute() else (ROOT / args.out)
    policy_path = args.policy if args.policy.is_absolute() else (ROOT / args.policy)
    input_doc = _load_json(input_path)
    policy_doc = _load_policy(policy_path)
    result = evaluate_fragility(input_doc, policy_doc=policy_doc)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"fragility_composite_v1: PASS -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
