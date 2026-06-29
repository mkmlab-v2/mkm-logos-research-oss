#!/usr/bin/env python3
"""Validate web_ops_regime_gate_v1 artifact and policy alignment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IN = ROOT / "reports/web_ops_regime_gate_v1_latest.json"
SCHEMA = ROOT / "docs/final/schemas/web_ops_regime_gate_v1.schema.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _minimal_validate(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if doc.get("schema") != "web_ops_regime_gate_v1":
        errors.append("schema_mismatch")
    if doc.get("research_only") is not True:
        errors.append("research_only_must_be_true")
    if doc.get("track_wall") != "b_track_research":
        errors.append("track_wall_must_be_b_track_research")
    for key in ("cost_policy", "probes", "conflict_resolver", "gate_pass"):
        if key not in doc:
            errors.append(f"missing_{key}")
    probes = doc.get("probes")
    if not isinstance(probes, list) or not probes:
        errors.append("probes_empty")
    else:
        for i, probe in enumerate(probes):
            if not isinstance(probe, dict):
                errors.append(f"probe_{i}_not_object")
                continue
            for key in ("probe_id", "raw", "repair_v2", "final_action", "outcome_class"):
                if key not in probe:
                    errors.append(f"probe_{i}_missing_{key}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in-json", type=Path, default=DEFAULT_IN)
    ap.add_argument("--require-gate-pass", action="store_true", default=False)
    ap.add_argument("--strict-hold", action="store_true", default=False)
    ap.add_argument("--require-dual-alignment", action="store_true", default=False)
    ap.add_argument("--fail-on-pointer-drift", action="store_true", default=False)
    args = ap.parse_args()

    if not args.in_json.is_file():
        print(json.dumps({"ok": False, "error": "missing_input", "path": str(args.in_json)}, ensure_ascii=False))
        return 2

    doc = _read_json(args.in_json)
    errors = _minimal_validate(doc)
    cost = doc.get("cost_policy") if isinstance(doc.get("cost_policy"), dict) else {}
    if not cost.get("no_gpu_spinup"):
        errors.append("no_gpu_spinup_false")
    if not cost.get("no_new_billing_charges"):
        errors.append("no_new_billing_charges_false")

    worst = str((doc.get("conflict_resolver") or {}).get("worst_final_action") or "")
    gate_pass = bool(doc.get("gate_pass"))

    if args.require_gate_pass and not gate_pass:
        errors.append("gate_pass_required_false")

    hold_ok = worst.startswith("HOLD_")
    if args.strict_hold and not hold_ok:
        errors.append("strict_hold_expected")

    dual_stats = {"probes_with_dual": 0, "alignment_pass": 0, "alignment_fail": 0}
    drift_detected = 0
    for i, probe in enumerate(doc.get("probes") or []):
        if not isinstance(probe, dict):
            continue
        dual = probe.get("dual_observation")
        if isinstance(dual, dict):
            dual_stats["probes_with_dual"] += 1
            if dual.get("alignment_pass"):
                dual_stats["alignment_pass"] += 1
            else:
                dual_stats["alignment_fail"] += 1
                if args.require_dual_alignment:
                    errors.append(f"probe_{i}_dual_alignment_fail")
        drift = probe.get("pointer_drift")
        if isinstance(drift, dict) and drift.get("drift_detected"):
            drift_detected += 1
            if args.fail_on_pointer_drift:
                errors.append(f"probe_{i}_pointer_drift")

    ok = not errors
    summary = {
        "ok": ok,
        "path": str(args.in_json),
        "schema_ref": str(SCHEMA),
        "gate_pass": gate_pass,
        "worst_final_action": worst,
        "combined_all_passed": doc.get("combined_all_passed"),
        "dual_observation": dual_stats,
        "pointer_drift_count": drift_detected,
        "errors": errors,
        "track_a_promotion": False,
        "research_only": True,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
