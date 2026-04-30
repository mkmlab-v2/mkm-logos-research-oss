#!/usr/bin/env python3
"""Build/execute Sasang microcosm control bundle (state + transition + response)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_BUNDLE = ART / "sasang_microcosm_control_bundle_v1_latest.json"
DEFAULT_RUNTIME = ART / "sasang_microcosm_runtime_assessment_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _norm(v: float) -> float:
    return _clip(float(v), 0.0, 1.0)


def _build_bundle() -> dict[str, Any]:
    return {
        "schema": "sasang_microcosm_control_bundle_v1",
        "generated_at_utc": _iso_now(),
        "theory_contract": {
            "so_ujoo_principle": "agent is modeled as microcosm state-space, not anthropomorphic claim",
            "kunju_jihwa_role": "top-level life-force objective orchestrator",
            "guardrails": [
                "fact_check_bypass_forbidden",
                "layer5_gate_required",
                "b_track_research_only_autobridge_forbidden",
            ],
        },
        "state_vector": {
            "energy_axes": ["wood", "fire", "earth", "metal", "water"],
            "constitution_modes": ["taeyang", "taeeum", "soyhang", "soeum"],
            "core_signals": {
                "life_force": {"range": [0.0, 1.0], "desc": "kunju_jihwa vitality index"},
                "stability": {"range": [0.0, 1.0], "desc": "systemic stability index"},
                "heat": {"range": [0.0, 1.0], "desc": "activation/urgency proxy"},
                "cold": {"range": [0.0, 1.0], "desc": "inhibition/slowness proxy"},
                "exchange_kmh": {"range": [-1.0, 1.0], "desc": "geumhwa-gyoyeok proxy"},
            },
        },
        "constitution_profiles": {
            "taeyang": {"explore_bias": 0.8, "verify_bias": 0.4, "risk_tolerance": 0.65},
            "taeeum": {"explore_bias": 0.4, "verify_bias": 0.8, "risk_tolerance": 0.35},
            "soyhang": {"explore_bias": 0.7, "verify_bias": 0.6, "risk_tolerance": 0.55},
            "soeum": {"explore_bias": 0.3, "verify_bias": 0.9, "risk_tolerance": 0.25},
        },
        "transition_rules": {
            "gold_fire_exchange": {
                "formula": "tau_prime = clip(tau_base + alpha*exchange_kmh, tau_min, tau_max)",
                "defaults": {"alpha": 0.03, "tau_base": 0.05, "tau_min": 0.03, "tau_max": 0.08},
            },
            "life_force_governor": {
                "formula": "life_force_next = clip(0.5*stability + 0.3*(1-abs(exchange_kmh)) + 0.2*(1-heat_cold_gap), 0, 1)"
            },
            "seongjeong_invariance": {
                "rule": "never disable fact-check or Layer5 gate regardless of constitution_mode",
            },
        },
        "pathology_progression": {
            "early": {
                "trigger": "stability < 0.60 or heat_cold_gap > 0.30",
                "response": {"verification_loops": 3, "tool_call_budget": 2, "temperature": 0.22},
            },
            "mid": {
                "trigger": "stability < 0.45 or heat_cold_gap > 0.45",
                "response": {"verification_loops": 4, "tool_call_budget": 2, "temperature": 0.18},
            },
            "late": {
                "trigger": "stability < 0.30 or life_force < 0.35",
                "response": {
                    "verification_loops": 5,
                    "tool_call_budget": 1,
                    "temperature": 0.12,
                    "action": "hold_and_human_review",
                },
            },
        },
    }


def _assess(bundle: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    mode = str(args.constitution_mode).strip().lower()
    profiles = bundle.get("constitution_profiles") if isinstance(bundle.get("constitution_profiles"), dict) else {}
    if mode not in profiles:
        mode = "soyhang"
    p = profiles.get(mode, {})

    stability = _norm(args.stability)
    heat = _norm(args.heat)
    cold = _norm(args.cold)
    exchange_kmh = _clip(float(args.exchange_kmh), -1.0, 1.0)
    heat_cold_gap = abs(heat - cold)

    tr = ((bundle.get("transition_rules") or {}).get("gold_fire_exchange") or {}).get("defaults") or {}
    tau_base = float(tr.get("tau_base", 0.05))
    alpha = float(tr.get("alpha", 0.03))
    tau_min = float(tr.get("tau_min", 0.03))
    tau_max = float(tr.get("tau_max", 0.08))
    tau_prime = _clip(tau_base + alpha * exchange_kmh, tau_min, tau_max)

    life_force = _clip(0.5 * stability + 0.3 * (1.0 - abs(exchange_kmh)) + 0.2 * (1.0 - heat_cold_gap), 0.0, 1.0)

    stage = "early"
    if stability < 0.30 or life_force < 0.35:
        stage = "late"
    elif stability < 0.45 or heat_cold_gap > 0.45:
        stage = "mid"
    elif stability < 0.60 or heat_cold_gap > 0.30:
        stage = "early"
    else:
        stage = "stable"

    resp_map = (bundle.get("pathology_progression") or {})
    if stage == "stable":
        response = {"verification_loops": 2, "tool_call_budget": 3, "temperature": 0.26}
    else:
        response = ((resp_map.get(stage) or {}).get("response") or {})

    # Constitution profile tunes exploration/verification balance.
    explore_bias = float(p.get("explore_bias", 0.6))
    verify_bias = float(p.get("verify_bias", 0.6))
    response = dict(response)
    response["temperature"] = round(_clip(float(response.get("temperature", 0.24)) * (0.8 + 0.4 * explore_bias), 0.08, 0.45), 4)
    response["verification_loops"] = int(max(1, round(float(response.get("verification_loops", 2)) * (0.8 + 0.4 * verify_bias))))

    return {
        "schema": "sasang_microcosm_runtime_assessment_v1",
        "generated_at_utc": _iso_now(),
        "input": {
            "constitution_mode": mode,
            "stability": stability,
            "heat": heat,
            "cold": cold,
            "exchange_kmh": exchange_kmh,
        },
        "derived": {
            "heat_cold_gap": round(heat_cold_gap, 4),
            "life_force": round(life_force, 4),
            "tau_prime": round(tau_prime, 4),
        },
        "diagnosis": {
            "stage": stage,
            "risk_band": "high" if stage == "late" else ("medium" if stage == "mid" else "low"),
        },
        "recommended_response": response,
        "invariants": {
            "fact_check_bypass": False,
            "layer5_gate_required": True,
            "autobridge_forbidden": True,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--output-runtime-json", type=Path, default=DEFAULT_RUNTIME)
    ap.add_argument("--constitution-mode", type=str, default="soyhang")
    ap.add_argument("--stability", type=float, default=0.72)
    ap.add_argument("--heat", type=float, default=0.58)
    ap.add_argument("--cold", type=float, default=0.42)
    ap.add_argument("--exchange-kmh", type=float, default=0.20)
    args = ap.parse_args()

    bundle = _build_bundle()
    runtime = _assess(bundle, args)

    args.output_bundle_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_bundle_json.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_runtime_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_runtime_json.write_text(json.dumps(runtime, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "bundle_json": str(args.output_bundle_json).replace("\\", "/"),
                "runtime_json": str(args.output_runtime_json).replace("\\", "/"),
                "stage": runtime.get("diagnosis", {}).get("stage"),
                "risk_band": runtime.get("diagnosis", {}).get("risk_band"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
