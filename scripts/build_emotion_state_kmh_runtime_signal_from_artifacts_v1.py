#!/usr/bin/env python3
"""Derive runtime z_km signal from current governance artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_L1 = ART / "layer1_router_benchmark_latest.json"
DEFAULT_L5 = ART / "layer5_policy_gate_benchmark_latest.json"
DEFAULT_DRIFT = ART / "layer1_layer5_baseline_drift_check_latest.json"
DEFAULT_OUT = ART / "emotion_state_kmh_runtime_signal_latest.json"


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


def _num(v: Any, d: float) -> float:
    try:
        return float(v)
    except Exception:
        return float(d)


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--layer1-json", type=Path, default=DEFAULT_L1)
    ap.add_argument("--layer5-json", type=Path, default=DEFAULT_L5)
    ap.add_argument("--drift-json", type=Path, default=DEFAULT_DRIFT)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    l1 = _read_json(args.layer1_json)
    l5 = _read_json(args.layer5_json)
    drift = _read_json(args.drift_json)

    l1_acc = _num((l1.get("metrics") or {}).get("accuracy"), 0.0)
    l5_recall = _num((l5.get("metrics") or {}).get("recall_block"), 0.0)
    l5_fpr = _num((l5.get("metrics") or {}).get("false_positive_rate"), 1.0)
    drift_pass = str(drift.get("status") or "") == "PASS"

    # Positive when reliability is high, negative when FPR risk dominates.
    raw = 0.5 * (l1_acc + l5_recall) - 1.0 * l5_fpr + (0.1 if drift_pass else -0.1)
    z_km = _clip(2.0 * (raw - 0.5), -1.0, 1.0)

    out = {
        "schema": "emotion_state_kmh_runtime_signal_v1",
        "generated_at_utc": _iso_now(),
        "source": "governance_artifacts_derived",
        "inputs": {
            "layer1_json": str(args.layer1_json).replace("\\", "/"),
            "layer5_json": str(args.layer5_json).replace("\\", "/"),
            "drift_json": str(args.drift_json).replace("\\", "/"),
        },
        "metrics": {
            "layer1_accuracy": l1_acc,
            "layer5_recall": l5_recall,
            "layer5_fpr": l5_fpr,
            "baseline_drift_pass": drift_pass,
        },
        "z_km": z_km,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "z_km": z_km}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
