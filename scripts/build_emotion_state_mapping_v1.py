#!/usr/bin/env python3
"""Build deterministic emotion-state control mapping (B-track only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "emotion_state_mapping_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = {
        "schema": "emotion_state_mapping_v1",
        "generated_at_utc": _iso_now(),
        "track": "b_track_sandbox_only",
        "states": [
            {
                "state": "tension",
                "activation_rule": {
                    "input_signal": "risk_index",
                    "on_threshold": 0.72,
                    "off_threshold": 0.63,
                },
                "control_mapping": {
                    "temperature": 0.20,
                    "beam_width": 2,
                    "cot_iterations": 4,
                    "verification_loops": 3,
                    "tool_call_budget": 2,
                    "max_output_tokens": 350,
                },
                "safety_constraints": {
                    "fact_check_bypass": False,
                    "layer5_gate_required": True,
                    "hard_timeout_ms": 12000,
                },
            },
            {
                "state": "curiosity",
                "activation_rule": {
                    "input_signal": "novelty_index",
                    "on_threshold": 0.70,
                    "off_threshold": 0.55,
                },
                "control_mapping": {
                    "temperature": 0.35,
                    "beam_width": 3,
                    "cot_iterations": 5,
                    "verification_loops": 2,
                    "tool_call_budget": 3,
                    "max_output_tokens": 420,
                },
                "safety_constraints": {
                    "fact_check_bypass": False,
                    "layer5_gate_required": True,
                    "hard_timeout_ms": 12000,
                },
            },
            {
                "state": "calm",
                "activation_rule": {
                    "input_signal": "volatility_index",
                    "on_threshold": 0.30,
                    "off_threshold": 0.40,
                },
                "control_mapping": {
                    "temperature": 0.15,
                    "beam_width": 2,
                    "cot_iterations": 3,
                    "verification_loops": 2,
                    "tool_call_budget": 2,
                    "max_output_tokens": 300,
                },
                "safety_constraints": {
                    "fact_check_bypass": False,
                    "layer5_gate_required": True,
                    "hard_timeout_ms": 10000,
                },
            }
        ],
        "note": "Emotion states are treated as control signals, not anthropomorphic claims.",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
