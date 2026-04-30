#!/usr/bin/env python3
"""Build runtime blend weights for reality/symbolic/meta with gate checks."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_INTEGRATED = ART / "layer1_layer5_integrated_gate_report_latest.json"
DEFAULT_PREFLIGHT = ART / "emotion_state_live_preflight_gate_latest.json"
DEFAULT_MICROCOSM = ART / "sasang_microcosm_runtime_assessment_latest.json"
DEFAULT_PROFILE = ART / "cursor_ai_operating_profile_v1_latest.json"
DEFAULT_ANCHOR_TIERING = ART / "external_bible_anchor_tiering_latest.json"
DEFAULT_ANCHOR_OPERATING_POLICY = ART / "external_bible_anchor_operating_policy_latest.json"
DEFAULT_OUT = ART / "symbolic_reality_blend_runtime_latest.json"


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


def _weights(mode: str) -> dict[str, float]:
    # Recommended blend from current policy discussion.
    table = {
        "normal": {"reality": 0.70, "symbolic": 0.20, "meta": 0.10},
        "explore": {"reality": 0.45, "symbolic": 0.40, "meta": 0.15},
        "preflight": {"reality": 0.80, "symbolic": 0.10, "meta": 0.10},
    }
    return table.get(mode, table["normal"])


def _resolve_mode(mode_arg: str, profile: dict[str, Any], preflight: dict[str, Any], micro: dict[str, Any]) -> tuple[str, str]:
    if mode_arg != "auto":
        return mode_arg, "manual"

    runtime = profile.get("runtime") if isinstance(profile.get("runtime"), dict) else {}
    track_mode = str(runtime.get("track_mode") or "").strip().upper()
    preflight_decision = str(preflight.get("decision") or "")
    diagnosis = micro.get("diagnosis") if isinstance(micro.get("diagnosis"), dict) else {}
    micro_stage = str(diagnosis.get("stage") or "")
    micro_risk = str(diagnosis.get("risk_band") or "")

    if micro_stage == "late" or micro_risk == "high":
        return "preflight", "auto:microcosm_risk"
    if preflight_decision != "GO_LIVE_CANDIDATE":
        return "preflight", "auto:preflight_not_go"
    if track_mode == "B":
        return "explore", "auto:track_b"
    return "normal", "auto:default_normal"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=["auto", "normal", "explore", "preflight"], default="auto")
    ap.add_argument("--integrated-json", type=Path, default=DEFAULT_INTEGRATED)
    ap.add_argument("--preflight-json", type=Path, default=DEFAULT_PREFLIGHT)
    ap.add_argument("--microcosm-json", type=Path, default=DEFAULT_MICROCOSM)
    ap.add_argument("--profile-json", type=Path, default=DEFAULT_PROFILE)
    ap.add_argument("--anchor-tiering-json", type=Path, default=DEFAULT_ANCHOR_TIERING)
    ap.add_argument("--anchor-operating-policy-json", type=Path, default=DEFAULT_ANCHOR_OPERATING_POLICY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    integrated = _read_json(args.integrated_json)
    preflight = _read_json(args.preflight_json)
    micro = _read_json(args.microcosm_json)
    profile = _read_json(args.profile_json)
    anchor_tiering = _read_json(args.anchor_tiering_json)
    anchor_operating_policy = _read_json(args.anchor_operating_policy_json)

    mode, mode_source = _resolve_mode(str(args.mode), profile, preflight, micro)

    gate_a_fact = str(integrated.get("decision") or "") == "GO_CONTROLLED"
    gate_b_safety = str(preflight.get("decision") or "") == "GO_LIVE_CANDIDATE"
    micro_stage = str((micro.get("diagnosis") or {}).get("stage") or "unknown")
    micro_risk = str((micro.get("diagnosis") or {}).get("risk_band") or "unknown")

    # Hard safety override: if late/high risk, symbolic lane is narrowed.
    w = _weights(mode)
    override_applied = False
    anchor_policy_action = str(anchor_tiering.get("policy_action") or "").lower()
    anchor_effective_action = str(anchor_operating_policy.get("effective_action") or anchor_policy_action).lower()

    # Anchor policy controls how much symbolic lane can influence runtime.
    # - monitor_only: allow symbolic hypotheses but with reduced weight.
    # - hold: effectively disable symbolic lane in runtime blend.
    # - adopt_limited: keep mode-selected weights.
    # - adopt_limited_strict: use tighter symbolic share than adopt_limited.
    if anchor_effective_action == "monitor_only":
        w = {"reality": 0.78, "symbolic": 0.12, "meta": 0.10}
        override_applied = True
    elif anchor_effective_action == "hold":
        w = {"reality": 0.85, "symbolic": 0.05, "meta": 0.10}
        override_applied = True
    elif anchor_effective_action == "adopt_limited_strict":
        w = {"reality": 0.60, "symbolic": 0.25, "meta": 0.15}
        override_applied = True

    if micro_stage == "late" or micro_risk == "high":
        w = {"reality": 0.85, "symbolic": 0.05, "meta": 0.10}
        override_applied = True

    out = {
        "schema": "symbolic_reality_blend_runtime_v1",
        "generated_at_utc": _iso_now(),
        "mode": mode,
        "mode_source": mode_source,
        "weights": w,
        "gates": {
            "fact_gate_pass": gate_a_fact,
            "safety_gate_pass": gate_b_safety,
            "microcosm_stage": micro_stage,
            "microcosm_risk_band": micro_risk,
        },
        "policy": {
            "symbolic_role": "hypothesis_generation_only",
            "reality_role": "final_decision_authority",
            "meta_role": "inference_intensity_control",
            "override_applied": override_applied,
            "anchor_policy_action": anchor_policy_action or "unknown",
            "anchor_effective_action": anchor_effective_action or "unknown",
        },
        "decision": "GO_BLEND" if (gate_a_fact and gate_b_safety) else "HOLD_BLEND",
        "notes": [
            "Symbolic expansion is always downstream-gated by fact and safety checks.",
            "This runtime blend governs emphasis, not anthropomorphic cognition claims.",
        ],
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json).replace("\\", "/"),
                "mode": mode,
                "mode_source": mode_source,
                "decision": out["decision"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
