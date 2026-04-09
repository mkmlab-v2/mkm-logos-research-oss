#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_scripts_dir = Path(__file__).resolve().parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

ART = ROOT / "docs" / "final" / "artifacts"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(name: str) -> dict[str, Any]:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def _read_resolved(artifact_path: Path) -> dict[str, Any]:
    from trackb_artifact_alias_util import resolve_alias_doc

    doc, _ = resolve_alias_doc(ROOT, artifact_path)
    return doc


def _resolve_action_layer_gate_path() -> Path:
    layer = ART / "trackb_action_layer_gate_pilot_latest.json"
    leg = ART / "trackb_action_gate_pilot_latest.json"
    if layer.is_file():
        return layer
    if leg.is_file():
        return leg
    raise FileNotFoundError(
        "missing action layer gate pilot: expected "
        "trackb_action_layer_gate_pilot_latest.json or legacy trackb_action_gate_pilot_latest.json"
    )


def _resolve_selective_state_artifact() -> Path | None:
    candidates = [
        ART / "trackb_action_layer_selective_state_sim_triggercase_latest.json",
        ART / "trackb_action_layer_selective_state_sim_latest.json",
        ART / "trackb_selective_state_sim_triggercase_latest.json",
        ART / "trackb_selective_state_sim_latest.json",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Track B weekly gate recheck with action-gate metrics")
    ap.add_argument("--out", default=str(ART / "trackb_weekly_gate_recheck_latest.json"))
    ap.add_argument("--semantic-min", type=float, default=0.80)
    ap.add_argument("--collision-max", type=float, default=0.01)
    ap.add_argument("--oov-max", type=float, default=0.15)
    ap.add_argument("--oov-stress-semantic-floor", type=float, default=0.75)
    ap.add_argument("--action-fire-min", type=float, default=0.30)
    ap.add_argument("--fallback-max", type=float, default=0.70)
    args = ap.parse_args()

    by_domain = _read("trackb_semantic_eval_by_domain_latest.json")
    oov = _read("trackb_oov_collision_sweep_latest.json")
    det = _read("trackb_determinism_repeatcheck_latest.json")
    action_path = _resolve_action_layer_gate_path()
    action = _read_resolved(action_path)

    gates = {
        "semantic_score_min": args.semantic_min,
        "collision_rate_max": args.collision_max,
        "oov_rate_max": args.oov_max,
        "determinism_required": True,
        "oov_stress_semantic_floor_at_0p1": args.oov_stress_semantic_floor,
        "action_fire_rate_min": args.action_fire_min,
        "fallback_rate_max": args.fallback_max,
    }

    domain_checks: dict[str, Any] = {}
    all_domain_ok = True
    for domain, payload in by_domain["domains"].items():
        m = payload["metrics"]
        c = {
            "semantic_ok": m["average_semantic_score"] >= gates["semantic_score_min"],
            "collision_ok": m["collision_rate_proxy"] <= gates["collision_rate_max"],
            "oov_ok": m["oov_rate_avg"] <= gates["oov_rate_max"],
        }
        domain_checks[domain] = c
        all_domain_ok = all_domain_ok and all(c.values())

    oov_stress_checks: dict[str, Any] = {}
    all_oov_stress_ok = True
    for domain, payload in oov["domains"].items():
        at_01 = [x for x in payload["sweep"] if abs(float(x["oov_ratio"]) - 0.1) < 1e-9][0]["metrics"]
        c = {
            "semantic_floor_ok": at_01["average_semantic_score"] >= gates["oov_stress_semantic_floor_at_0p1"],
            "oov_directional_degradation_expected": True,
        }
        oov_stress_checks[domain] = c
        all_oov_stress_ok = all_oov_stress_ok and c["semantic_floor_ok"]

    determinism_ok = bool(det.get("overall_deterministic")) == gates["determinism_required"]

    summary = action.get("summary", {})
    event_count = max(1, int(summary.get("event_count", 0)))
    action_fire_count = int(summary.get("action_fire_count", 0))
    fallback_count = int(summary.get("fallback_count", 0))
    action_fire_rate = action_fire_count / event_count
    fallback_rate = fallback_count / event_count
    action_checks = {
        "event_count": event_count,
        "action_fire_count": action_fire_count,
        "fallback_count": fallback_count,
        "action_fire_rate": round(action_fire_rate, 8),
        "fallback_rate": round(fallback_rate, 8),
        "action_fire_rate_ok": action_fire_rate >= gates["action_fire_rate_min"],
        "fallback_rate_ok": fallback_rate <= gates["fallback_rate_max"],
    }

    final_ok = (
        all_domain_ok
        and all_oov_stress_ok
        and determinism_ok
        and action_checks["action_fire_rate_ok"]
        and action_checks["fallback_rate_ok"]
    )

    selective_path = _resolve_selective_state_artifact()
    selective_checks: dict[str, Any] | None = None
    selective_resolved: Path | None = None
    if selective_path is not None:
        from trackb_artifact_alias_util import resolve_alias_doc

        sim_doc, selective_resolved = resolve_alias_doc(ROOT, selective_path)
        ssum = sim_doc.get("summary", {})
        logs = sim_doc.get("logs", [])
        reasons = [x.get("output", {}).get("reason") for x in logs if isinstance(x, dict)]
        selective_checks = {
            "artifact_relative": str(selective_resolved.relative_to(ROOT)).replace("\\", "/"),
            "summary": ssum,
            "observed_fallback_reasons": sorted({r for r in reasons if r}),
            "cooldown_observed": "cooldown_active" in reasons,
            "policy_blocked_observed": "policy_blocked" in reasons,
            "action_trigger_observed": int(ssum.get("action_triggered_count", 0) or 0) > 0,
            "fact_safe_note": (
                "selective_state_sim is a logic MVP (forget + accumulate + gate). "
                "Not a Mamba/SSM model forward-pass benchmark."
            ),
        }

    inputs: dict[str, str] = {
        "by_domain": "docs/final/artifacts/trackb_semantic_eval_by_domain_latest.json",
        "oov_sweep": "docs/final/artifacts/trackb_oov_collision_sweep_latest.json",
        "determinism": "docs/final/artifacts/trackb_determinism_repeatcheck_latest.json",
        "action_layer_gate": "docs/final/artifacts/trackb_action_layer_gate_pilot_latest.json",
    }
    if selective_resolved is not None:
        inputs["action_layer_selective_state_sim"] = str(selective_resolved.relative_to(ROOT)).replace(
            "\\", "/"
        )

    checks: dict[str, Any] = {
        "domain_gate_checks": domain_checks,
        "oov_stress_checks": oov_stress_checks,
        "determinism_ok": determinism_ok,
        "action_layer_gate_checks": action_checks,
    }
    if selective_checks is not None:
        checks["action_layer_selective_state_checks"] = selective_checks

    out = {
        "schema": "trackb_weekly_gate_recheck_v4",
        "generated_at_utc": _utc_now(),
        "measured_item": "Weekly recheck for historical-formula utility on Track B (action-gate + selective-state MVP)",
        "artifact_inputs": inputs,
        "gates": gates,
        "checks": checks,
        "decision": "GO_RESEARCH" if final_ok else "HOLD_RESEARCH",
        "out_of_scope": "No production promotion, no trading trigger, no billing claim.",
    }

    out_path = Path(args.out) if Path(args.out).is_absolute() else (ROOT / args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
