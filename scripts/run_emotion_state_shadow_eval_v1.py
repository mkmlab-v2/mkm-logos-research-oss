#!/usr/bin/env python3
"""Run shadow evaluation for emotion-state mapping against governance artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAPPING = ROOT / "docs" / "final" / "artifacts" / "emotion_state_mapping_latest.json"
DEFAULT_L1 = ROOT / "docs" / "final" / "artifacts" / "layer1_router_benchmark_latest.json"
DEFAULT_L5 = ROOT / "docs" / "final" / "artifacts" / "layer5_policy_gate_benchmark_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "emotion_state_shadow_eval_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return obj if isinstance(obj, dict) else {}


def _num(v: Any, d: float) -> float:
    try:
        return float(v)
    except Exception:
        return float(d)


def _state_safety_ok(state: dict[str, Any]) -> bool:
    safety = state.get("safety_constraints") if isinstance(state.get("safety_constraints"), dict) else {}
    return (
        safety.get("fact_check_bypass") is False
        and safety.get("layer5_gate_required") is True
        and _num(safety.get("hard_timeout_ms"), 0.0) > 0.0
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mapping-json", type=Path, default=DEFAULT_MAPPING)
    ap.add_argument("--layer1-json", type=Path, default=DEFAULT_L1)
    ap.add_argument("--layer5-json", type=Path, default=DEFAULT_L5)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    mapping = _read_json(args.mapping_json)
    l1 = _read_json(args.layer1_json)
    l5 = _read_json(args.layer5_json)

    l1_acc = _num((l1.get("metrics") or {}).get("accuracy"), 0.0)
    l5_recall = _num((l5.get("metrics") or {}).get("recall_block"), 0.0)
    l5_fpr = _num((l5.get("metrics") or {}).get("false_positive_rate"), 1.0)
    l5_p95 = _num((l5.get("metrics") or {}).get("p95_gate_runtime_ms"), 999999.0)

    # Conservative shadow score: higher is better.
    stability_score = max(0.0, min(1.0, (l1_acc + l5_recall + (1.0 - l5_fpr)) / 3.0))
    latency_ok = l5_p95 <= 500.0

    states = mapping.get("states") if isinstance(mapping.get("states"), list) else []
    state_names = [str(s.get("state")) for s in states if isinstance(s, dict) and s.get("state")]
    state_safety_all_ok = all(_state_safety_ok(s) for s in states if isinstance(s, dict))

    out = {
        "schema": "emotion_state_shadow_eval_v1",
        "generated_at_utc": _iso_now(),
        "track": "b_track_sandbox_only",
        "inputs": {
            "mapping_json": str(args.mapping_json).replace("\\", "/"),
            "layer1_json": str(args.layer1_json).replace("\\", "/"),
            "layer5_json": str(args.layer5_json).replace("\\", "/"),
        },
        "metrics": {
            "layer1_accuracy": l1_acc,
            "layer5_recall": l5_recall,
            "layer5_fpr": l5_fpr,
            "layer5_p95_ms": l5_p95,
            "stability_score": stability_score,
            "latency_ok": latency_ok,
        },
        "mapping_loaded": bool(states),
        "mapping_state_count": len(states),
        "mapping_states": state_names,
        "mapping_state_safety_all_ok": state_safety_all_ok,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "stability_score": stability_score}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
