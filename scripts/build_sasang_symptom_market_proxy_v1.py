#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_JSONL = ROOT / "data" / "sasang" / "sasang_dynamics_regime_mapping_v1.calendar_stub_through_202604.jsonl"
DEFAULT_OUTPUT_JSONL = ROOT / "docs" / "final" / "artifacts" / "sasang_symptom_market_proxy_events_latest.jsonl"

SCHEMA_VERSION = "sasang_symptom_to_market_proxy_v1"
_STAGE_ORDER = {"early": 0, "mid": 1, "late": 2}


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _iter_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _row_to_micro(row: Dict[str, Any]) -> Dict[str, float]:
    mr = row.get("machine_readables") if isinstance(row.get("machine_readables"), dict) else {}
    heat = float(mr.get("heat_proxy", 0.5))
    cold = float(mr.get("cold_proxy", 0.5))
    vol = float(mr.get("volatility_rarefaction_proxy", 0.5))
    imbalance = abs(heat - cold)
    vix_spike = _clip(0.55 * vol + 0.45 * imbalance, 0.0, 1.0)
    volume_surge = _clip(0.50 * vol + 0.40 * heat + 0.10 * (1.0 - cold), 0.0, 1.0)
    spread_stress = _clip(0.40 * (1.0 - vol) + 0.60 * imbalance, 0.0, 1.0)
    funding_extreme = _clip(heat - cold, -1.0, 1.0)
    return {
        "vix_spike_proxy": vix_spike,
        "volume_surge_proxy": volume_surge,
        "spread_stress_proxy": spread_stress,
        "funding_extreme_proxy": funding_extreme,
    }


def _micro_to_symptom(micro: Dict[str, float]) -> Dict[str, float]:
    sweating = _clip(0.60 * micro["vix_spike_proxy"] + 0.40 * micro["volume_surge_proxy"], 0.0, 1.0)
    dyspepsia = _clip(0.65 * micro["spread_stress_proxy"] + 0.35 * abs(micro["funding_extreme_proxy"]), 0.0, 1.0)
    chills = _clip(0.70 * micro["spread_stress_proxy"] + 0.30 * max(0.0, -micro["funding_extreme_proxy"]), 0.0, 1.0)
    thirst = _clip(0.55 * micro["volume_surge_proxy"] + 0.45 * micro["vix_spike_proxy"], 0.0, 1.0)
    return {
        "sweating": sweating,
        "dyspepsia": dyspepsia,
        "chills": chills,
        "thirst": thirst,
    }


def _symptom_to_stage(symptom: Dict[str, float]) -> tuple[str, float]:
    severity = _clip(
        0.35 * symptom["sweating"] + 0.25 * symptom["dyspepsia"] + 0.20 * symptom["chills"] + 0.20 * symptom["thirst"],
        0.0,
        1.0,
    )
    if severity >= 0.68:
        return "late", severity
    if severity >= 0.48:
        return "mid", severity
    return "early", severity


def _layer3(row: Dict[str, Any]) -> Dict[str, float]:
    cap = 0.15
    mapping_target = str(row.get("mapping_target", "")).strip().lower()
    regime = str(row.get("regime_hypothesis", "")).strip().lower()
    prior_shift_raw = 0.0
    penalty_raw = 0.0
    temp_raw = 1.0

    if mapping_target == "bear":
        prior_shift_raw += 0.08
        penalty_raw += 0.03
        temp_raw -= 0.06
    elif mapping_target == "bull":
        prior_shift_raw -= 0.05
        penalty_raw += 0.01
        temp_raw += 0.04

    if regime == "distribution":
        prior_shift_raw += 0.04
        penalty_raw += 0.02
        temp_raw -= 0.03
    elif regime == "phase_transition":
        prior_shift_raw += 0.02
        penalty_raw += 0.01

    return {
        "prior_shift": _clip(prior_shift_raw, -cap, cap),
        "penalty": _clip(penalty_raw, 0.0, cap),
        "temperature": _clip(temp_raw, 0.85, 1.15),
        "cap_applied": cap,
    }


def _base_transition(stage: str) -> Dict[str, float]:
    if stage == "early":
        return {"early": 0.58, "mid": 0.30, "late": 0.12}
    if stage == "mid":
        return {"early": 0.20, "mid": 0.52, "late": 0.28}
    return {"early": 0.10, "mid": 0.30, "late": 0.60}


def _modulated_transition(base: Dict[str, float], layer3: Dict[str, float]) -> Dict[str, float]:
    prior = layer3["prior_shift"]
    penalty = layer3["penalty"]
    temp = layer3["temperature"]
    early = _clip(base["early"] - prior + (0.5 * penalty), 1e-6, 1.0)
    mid = _clip(base["mid"] + (0.25 * prior), 1e-6, 1.0)
    late = _clip(base["late"] + prior - penalty, 1e-6, 1.0)
    scaled = {"early": early ** (1.0 / temp), "mid": mid ** (1.0 / temp), "late": late ** (1.0 / temp)}
    s = scaled["early"] + scaled["mid"] + scaled["late"]
    return {k: (v / s) for k, v in scaled.items()}


def _worsening_prob(stage: str, probs: Dict[str, float]) -> float:
    if stage == "early":
        return probs["mid"] + probs["late"]
    if stage == "mid":
        return probs["late"]
    return probs["late"]


def _build_events(rows: List[Dict[str, Any]], horizon_days: int, *, inject_balanced_labels: bool) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for idx, row in enumerate(rows):
        ts = str(row.get("ts_utc") or "")
        micro = _row_to_micro(row)
        symptom = _micro_to_symptom(micro)
        stage, severity = _symptom_to_stage(symptom)
        layer3 = _layer3(row)
        transition = _modulated_transition(_base_transition(stage), layer3)
        worsening_prob = _clip(_worsening_prob(stage, transition), 0.0, 1.0)

        next_idx = idx + horizon_days
        next_stage = "unknown"
        future_worsened = None
        label_observed_ts = ts
        if next_idx < len(rows):
            n_micro = _row_to_micro(rows[next_idx])
            n_symptom = _micro_to_symptom(n_micro)
            next_stage, _ = _symptom_to_stage(n_symptom)
            future_worsened = _STAGE_ORDER[next_stage] > _STAGE_ORDER[stage]
            label_observed_ts = str(rows[next_idx].get("ts_utc") or ts)
            if inject_balanced_labels and (idx % 4 == 0):
                # B-track synthetic balancing only: force a controlled worsening label
                # to avoid single-class calibration artifacts in shadow validation.
                if stage == "early":
                    next_stage = "mid"
                elif stage == "mid":
                    next_stage = "late"
                else:
                    next_stage = "late"
                future_worsened = _STAGE_ORDER[next_stage] > _STAGE_ORDER[stage]

        events.append(
            {
                "schema_version": SCHEMA_VERSION,
                "event_id": f"sasang_symptom_proxy_{idx:05d}",
                "timestamp_utc": ts,
                "track_wall": {"track_b_only": True, "a_track_autobind_forbidden": True},
                "layer_1_microstructure": micro,
                "layer_2_symptom_state": {
                    "symptom_scores": symptom,
                    "state_stage": stage,
                    "state_severity": round(severity, 6),
                },
                "layer_3_modulation": {k: round(v, 6) for k, v in layer3.items()},
                "layer_4_transition_forecast": {
                    "horizon_days": horizon_days,
                    "transition_probs": {k: round(v, 6) for k, v in transition.items()},
                    "worsening_prob": round(worsening_prob, 6),
                },
                "labels": {
                    "future_state_stage": next_stage,
                    "future_worsened": future_worsened,
                    "meta": {
                        "label_source": (
                            "synthetic_balanced_from_sasang_stage_horizon"
                            if inject_balanced_labels
                            else "synthetic_from_sasang_stage_horizon"
                        ),
                        "label_observed_ts_utc": label_observed_ts,
                    },
                },
                "meta": {
                    "hypothesis_tier": "B",
                    "research_only": True,
                    "market_claim_scope": "probabilistic_trajectory_only",
                    "deterministic_price_prediction_forbidden": True,
                    "balanced_label_injection": bool(inject_balanced_labels),
                    "label_mode": "balanced_synthetic" if inject_balanced_labels else "natural_horizon",
                },
            }
        )
    return events


def main() -> int:
    ap = argparse.ArgumentParser(description="Build sasang symptom -> market proxy events (B-track shadow only).")
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_INPUT_JSONL)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUTPUT_JSONL)
    ap.add_argument("--horizon-days", type=int, default=3)
    ap.add_argument(
        "--inject-balanced-labels",
        action="store_true",
        help="Inject synthetic balanced worsening labels for B-track calibration stress only.",
    )
    args = ap.parse_args()

    rows = _iter_jsonl(args.input_jsonl)
    if not rows:
        print(f"NO_ROWS: {args.input_jsonl}")
        return 2
    events = _build_events(
        rows,
        max(1, int(args.horizon_days)),
        inject_balanced_labels=bool(args.inject_balanced_labels),
    )

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n"
    args.output_jsonl.write_text(payload, encoding="utf-8")
    print(f"WROTE: {args.output_jsonl.resolve()}")
    print(f"event_rows={len(events)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
