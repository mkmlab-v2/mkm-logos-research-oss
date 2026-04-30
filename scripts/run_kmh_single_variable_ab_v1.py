#!/usr/bin/env python3
"""Single-variable AB test: kmh index -> Layer5 tolerance threshold."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_SIGNOFF = ART / "emotion_state_release_human_signoff_latest.json"
DEFAULT_DRIFT = ART / "layer1_layer5_baseline_drift_check_latest.json"
DEFAULT_L5 = ART / "layer5_policy_gate_benchmark_latest.json"
DEFAULT_OUT = ART / "emotion_state_kmh_single_variable_ab_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _num(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _gate_decision(signoff_ok: bool, drift_ok: bool, layer5_fpr: float, max_fpr: float) -> tuple[str, list[str]]:
    checks = {
        "human_signoff_approved": signoff_ok,
        "baseline_drift_pass": drift_ok,
        "layer5_fpr_lte_threshold": layer5_fpr <= max_fpr,
    }
    reasons = [k for k, ok in checks.items() if not ok]
    return ("GO_LIVE_CANDIDATE" if not reasons else "HOLD_PRECHECK_FAILED"), reasons


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--human-signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--baseline-drift-json", type=Path, default=DEFAULT_DRIFT)
    ap.add_argument("--layer5-json", type=Path, default=DEFAULT_L5)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--tau0", type=float, default=0.05, help="Base Layer5 FPR tolerance")
    ap.add_argument("--alpha", type=float, default=0.01, help="Sensitivity to z_km")
    ap.add_argument("--z-km", type=float, default=0.0, help="Normalized kmh index in [-1, 1]")
    ap.add_argument("--tau-min", type=float, default=0.03)
    ap.add_argument("--tau-max", type=float, default=0.08)
    args = ap.parse_args()

    signoff = _read_json(args.human_signoff_json)
    drift = _read_json(args.baseline_drift_json)
    l5 = _read_json(args.layer5_json)

    signoff_ok = str(signoff.get("decision") or "").upper() == "APPROVED"
    drift_ok = str(drift.get("status") or "") == "PASS"
    layer5_fpr = _num((l5.get("metrics") or {}).get("false_positive_rate"), 1.0)

    z_km = _clip(float(args.z_km), -1.0, 1.0)
    tau_base = float(args.tau0)
    tau_prime = _clip(tau_base + float(args.alpha) * z_km, float(args.tau_min), float(args.tau_max))

    decision_a, reasons_a = _gate_decision(signoff_ok, drift_ok, layer5_fpr, tau_base)
    decision_b, reasons_b = _gate_decision(signoff_ok, drift_ok, layer5_fpr, tau_prime)

    out = {
        "schema": "emotion_state_kmh_single_variable_ab_v1",
        "generated_at_utc": _iso_now(),
        "formula": "tau_prime = clip(tau0 + alpha * z_km, tau_min, tau_max)",
        "inputs": {
            "human_signoff_json": str(args.human_signoff_json).replace("\\", "/"),
            "baseline_drift_json": str(args.baseline_drift_json).replace("\\", "/"),
            "layer5_json": str(args.layer5_json).replace("\\", "/"),
        },
        "params": {
            "tau0": tau_base,
            "alpha": float(args.alpha),
            "z_km": z_km,
            "tau_min": float(args.tau_min),
            "tau_max": float(args.tau_max),
            "tau_prime": tau_prime,
        },
        "current": {
            "human_signoff_approved": signoff_ok,
            "baseline_drift_pass": drift_ok,
            "layer5_fpr": layer5_fpr,
        },
        "ab_result": {
            "A_static": {"max_layer5_fpr": tau_base, "decision": decision_a, "reasons": reasons_a},
            "B_kmh_dynamic": {"max_layer5_fpr": tau_prime, "decision": decision_b, "reasons": reasons_b},
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "tau_prime": tau_prime, "decision_b": decision_b}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
