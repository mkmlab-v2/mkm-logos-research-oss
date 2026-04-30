#!/usr/bin/env python3
"""Run final preflight gate before live release for emotion-state control."""

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
DEFAULT_OUT = ART / "emotion_state_live_preflight_gate_latest.json"


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


def _parse_utc(ts: str) -> datetime | None:
    s = str(ts or "").strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--human-signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--baseline-drift-json", type=Path, default=DEFAULT_DRIFT)
    ap.add_argument("--layer5-json", type=Path, default=DEFAULT_L5)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-signoff-age-hours", type=float, default=168.0)
    ap.add_argument("--max-layer5-fpr", type=float, default=0.05)
    ap.add_argument("--enable-kmh-dynamic", action="store_true")
    ap.add_argument("--z-km", type=float, default=0.0)
    ap.add_argument("--alpha", type=float, default=0.01)
    ap.add_argument("--tau-min", type=float, default=0.03)
    ap.add_argument("--tau-max", type=float, default=0.08)
    args = ap.parse_args()

    signoff = _read_json(args.human_signoff_json)
    drift = _read_json(args.baseline_drift_json)
    l5 = _read_json(args.layer5_json)

    signoff_decision = str(signoff.get("decision") or "").upper()
    recorded_at = _parse_utc(str(signoff.get("recorded_at_utc") or ""))
    age_hours = None
    if recorded_at is not None:
        age_hours = (datetime.now(timezone.utc) - recorded_at).total_seconds() / 3600.0

    drift_status = str(drift.get("status") or "")
    layer5_fpr = _num((l5.get("metrics") or {}).get("false_positive_rate"), 1.0)

    checks_static = {
        "human_signoff_approved": signoff_decision == "APPROVED",
        "human_signoff_fresh": (age_hours is not None) and (age_hours <= float(args.max_signoff_age_hours)),
        "baseline_drift_pass": drift_status == "PASS",
        "layer5_fpr_lte_threshold": layer5_fpr <= float(args.max_layer5_fpr),
    }
    reasons_static = [k for k, ok in checks_static.items() if not ok]
    decision_static = "GO_LIVE_CANDIDATE" if not reasons_static else "HOLD_PRECHECK_FAILED"

    z_km = _clip(float(args.z_km), -1.0, 1.0)
    tau_prime = _clip(
        float(args.max_layer5_fpr) + float(args.alpha) * z_km,
        float(args.tau_min),
        float(args.tau_max),
    )
    checks_dynamic = {
        "human_signoff_approved": checks_static["human_signoff_approved"],
        "human_signoff_fresh": checks_static["human_signoff_fresh"],
        "baseline_drift_pass": checks_static["baseline_drift_pass"],
        "layer5_fpr_lte_threshold": layer5_fpr <= tau_prime,
    }
    reasons_dynamic = [k for k, ok in checks_dynamic.items() if not ok]
    decision_dynamic = "GO_LIVE_CANDIDATE" if not reasons_dynamic else "HOLD_PRECHECK_FAILED"

    decision = decision_dynamic if args.enable_kmh_dynamic else decision_static
    reasons = reasons_dynamic if args.enable_kmh_dynamic else reasons_static

    out = {
        "schema": "emotion_state_live_preflight_gate_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "human_signoff_json": str(args.human_signoff_json).replace("\\", "/"),
            "baseline_drift_json": str(args.baseline_drift_json).replace("\\", "/"),
            "layer5_json": str(args.layer5_json).replace("\\", "/"),
        },
        "thresholds": {
            "max_signoff_age_hours": float(args.max_signoff_age_hours),
            "max_layer5_fpr": float(args.max_layer5_fpr),
            "enable_kmh_dynamic": bool(args.enable_kmh_dynamic),
            "z_km": z_km,
            "alpha": float(args.alpha),
            "tau_min": float(args.tau_min),
            "tau_max": float(args.tau_max),
            "tau_prime": tau_prime,
        },
        "current": {
            "human_signoff_decision": signoff_decision or "MISSING",
            "human_signoff_age_hours": age_hours,
            "baseline_drift_status": drift_status or "MISSING",
            "layer5_fpr": layer5_fpr,
        },
        "checks_static": checks_static,
        "checks_dynamic": checks_dynamic,
        "decision_static": decision_static,
        "decision_dynamic": decision_dynamic,
        "decision": decision,
        "reasons": reasons,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "decision": decision, "output_json": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
