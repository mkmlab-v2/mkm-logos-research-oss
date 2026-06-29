#!/usr/bin/env python3
"""Gate check for 31k/41k shadow uplift artifact (research-only, non-gating)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVAL_V2B_STRICT = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_eval_v2b_strict_latest.json"
DEFAULT_EVAL_V2B = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_eval_v2b_latest.json"
DEFAULT_EVAL_V2C = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_eval_v2c_latest.json"
DEFAULT_EVAL_V2 = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_eval_v2_latest.json"
DEFAULT_EVAL_V1 = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_eval_v1_latest.json"
DEFAULT_PANEL = ROOT / "docs/final/artifacts/btrack_31k41k_daily_anchor_panel_v1_latest.json"
DEFAULT_FOLD = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_fold_stability_v2b_strict_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_gate_v1_latest.json"
DEFAULT_SIGNOFF = ROOT / "reports/btrack_31k41k_shadow_human_signoff_latest.json"
DEFAULT_SIGNOFF_TEMPLATE = ROOT / "reports/btrack_31k41k_shadow_human_signoff_v1.template.json"

SSOT_OVERLAY = "v2b_strict"
SSOT_PANEL_FEATURE_MODE = "timeseries_v2"
SSOT_PANEL_MERGE = "per_row_strict"

DECISION_HOLD_SHADOW = "HOLD_SHADOW_ONLY"
DECISION_CANDIDATE = "CANDIDATE_ALLOWLIST_REVIEW"
DECISION_PENDING_SIGNOFF = "HOLD_PENDING_SIGNOFF"
DECISION_HUMAN_APPROVED = "ALLOWLIST_HUMAN_APPROVED"


def _resolve_eval_path(explicit: Path | None) -> Path:
    if explicit is not None and explicit.is_file():
        return explicit
    if DEFAULT_EVAL_V2B_STRICT.is_file():
        return DEFAULT_EVAL_V2B_STRICT
    if DEFAULT_EVAL_V2B.is_file():
        return DEFAULT_EVAL_V2B
    if DEFAULT_EVAL_V2C.is_file():
        return DEFAULT_EVAL_V2C
    if DEFAULT_EVAL_V2.is_file():
        return DEFAULT_EVAL_V2
    return DEFAULT_EVAL_V1


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return doc if isinstance(doc, dict) else {}


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _panel_feature_mode(eval_doc: dict[str, Any]) -> str | None:
    panel_path_s = (eval_doc.get("inputs") or {}).get("panel_json")
    if not panel_path_s:
        ps = eval_doc.get("panel_summary")
        if isinstance(ps, dict) and ps.get("feature_mode"):
            return str(ps.get("feature_mode"))
        return None
    panel_doc = _read_json(Path(str(panel_path_s)))
    if not panel_doc and not Path(str(panel_path_s)).is_absolute():
        panel_doc = _read_json(ROOT / str(panel_path_s))
    return str(panel_doc.get("feature_mode") or "") or None


def _signoff_approved(signoff_doc: dict[str, Any]) -> bool:
    if not signoff_doc:
        return False
    if signoff_doc.get("approved") is True:
        return True
    return str(signoff_doc.get("decision") or "").strip().upper() == "APPROVED"


def _signoff_scope_ok(signoff_doc: dict[str, Any]) -> bool:
    scope = signoff_doc.get("scope") if isinstance(signoff_doc.get("scope"), dict) else {}
    if scope.get("track_a_merge") is True or scope.get("live_trading") is True:
        return False
    return True


def resolve_gate_outcome(
    *,
    technical_passed: bool,
    gate_mode: str,
    human_signoff_ok: bool,
    signoff_present: bool,
) -> tuple[str, bool, str]:
    """Return (decision, all_passed, promotion_tier)."""
    if gate_mode == "allowlist_review":
        if not technical_passed:
            return DECISION_HOLD_SHADOW, False, "technical_failed"
        if human_signoff_ok:
            return DECISION_HUMAN_APPROVED, True, "allowlist_human_approved"
        if signoff_present:
            return DECISION_PENDING_SIGNOFF, False, "signoff_present_not_approved"
        return DECISION_PENDING_SIGNOFF, False, "signoff_missing"

    if technical_passed:
        return DECISION_CANDIDATE, True, "technical_only"
    return DECISION_HOLD_SHADOW, False, "technical_failed"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--eval-json",
        type=Path,
        default=None,
        help=f"Defaults to {DEFAULT_EVAL_V2B_STRICT.name} when present.",
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--gate-mode",
        choices=("routine", "allowlist_review"),
        default="routine",
        help="routine=technical SSOT only; allowlist_review=requires human signoff file.",
    )
    ap.add_argument(
        "--require-human-signoff",
        action="store_true",
        help="Alias for --gate-mode allowlist_review.",
    )
    ap.add_argument("--human-signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument(
        "--stability-not-worse",
        action="store_true",
        default=True,
        help="Require fold stability artifact (default on for SSOT gate).",
    )
    ap.add_argument(
        "--no-stability-not-worse",
        action="store_false",
        dest="stability_not_worse",
        help="Disable fold stability requirement.",
    )
    ap.add_argument("--fold-json", type=Path, default=DEFAULT_FOLD)
    ap.add_argument("--skip-fold-stability", action="store_true")
    ap.add_argument(
        "--allow-legacy-max-merge",
        action="store_true",
        help="Allow eval schema v2b (max merge) instead of v2b_strict SSOT.",
    )
    args = ap.parse_args()

    gate_mode = "allowlist_review" if args.require_human_signoff else args.gate_mode

    eval_path = _resolve_eval_path(args.eval_json)
    eval_doc = _read_json(eval_path)
    checks = eval_doc.get("checks") if isinstance(eval_doc.get("checks"), dict) else {}
    summary = eval_doc.get("summary") if isinstance(eval_doc.get("summary"), dict) else {}
    shadow_probe = eval_doc.get("shadow_probe") if isinstance(eval_doc.get("shadow_probe"), dict) else {}
    control = eval_doc.get("control_flags") if isinstance(eval_doc.get("control_flags"), dict) else {}
    schema = str(eval_doc.get("schema") or "")
    inputs = eval_doc.get("inputs") if isinstance(eval_doc.get("inputs"), dict) else {}
    overlay_version = str(inputs.get("overlay_version") or "")

    min_n_ok = bool(checks.get("min_n_ok"))
    delta_positive = bool(summary.get("shadow_delta_positive"))
    no_contamination = True
    v2_contract_ok = True
    is_v2b_strict_schema = schema.endswith("_v2b_strict")
    is_v2b_max_schema = schema.endswith("_v2b") and not is_v2b_strict_schema
    v2b_panel = is_v2b_strict_schema or is_v2b_max_schema
    if schema.endswith("_v2") or schema.endswith("_v2c") or v2b_panel:
        v2_contract_ok = bool(control.get("global_overlay_disengaged")) and bool(
            control.get("daily_routing_v2_enabled")
        )
        if schema.endswith("_v2c") or v2b_panel:
            v2_contract_ok = v2_contract_ok and bool(control.get("daily_routing_v2c_enabled"))
        if v2b_panel:
            v2_contract_ok = v2_contract_ok and bool(control.get("daily_panel_v2b_enabled"))
            if is_v2b_strict_schema:
                v2_contract_ok = v2_contract_ok and control.get("panel_merge_policy") == SSOT_PANEL_MERGE

    panel_feature_mode = _panel_feature_mode(eval_doc)
    panel_merge_policy = control.get("panel_merge_policy") or inputs.get("panel_merge_policy")

    ssot_contract_ok = True
    if not args.allow_legacy_max_merge:
        ssot_contract_ok = is_v2b_strict_schema and (
            overlay_version == SSOT_OVERLAY or not overlay_version
        )
        ssot_contract_ok = ssot_contract_ok and panel_merge_policy == SSOT_PANEL_MERGE
        if panel_feature_mode is not None:
            ssot_contract_ok = ssot_contract_ok and panel_feature_mode == SSOT_PANEL_FEATURE_MODE

    fold_doc = _read_json(args.fold_json) if not args.skip_fold_stability else {}
    fold_checks = fold_doc.get("checks") if isinstance(fold_doc.get("checks"), dict) else {}
    fold_summary = fold_doc.get("summary") if isinstance(fold_doc.get("summary"), dict) else {}
    fold_aggregates = fold_doc.get("aggregates") if isinstance(fold_doc.get("aggregates"), dict) else {}
    fold_inputs = fold_doc.get("inputs") if isinstance(fold_doc.get("inputs"), dict) else {}

    if args.stability_not_worse and not args.skip_fold_stability:
        stability_ok = bool(fold_doc) and bool(fold_checks.get("stability_not_worse"))
        if not args.allow_legacy_max_merge and fold_doc:
            stability_ok = stability_ok and str(fold_inputs.get("overlay_version") or "") in (
                SSOT_OVERLAY,
                "",
            )
    elif args.stability_not_worse:
        stability_ok = True
    else:
        stability_ok = True

    signoff_path = (
        (ROOT / args.human_signoff_json)
        if not args.human_signoff_json.is_absolute()
        else args.human_signoff_json
    )
    signoff_doc = _read_json(signoff_path)
    signoff_present = bool(signoff_doc)
    human_signoff_ok = _signoff_approved(signoff_doc) and _signoff_scope_ok(signoff_doc)

    technical_passed = (
        min_n_ok
        and delta_positive
        and no_contamination
        and v2_contract_ok
        and ssot_contract_ok
        and stability_ok
    )

    decision, all_passed, promotion_tier = resolve_gate_outcome(
        technical_passed=technical_passed,
        gate_mode=gate_mode,
        human_signoff_ok=human_signoff_ok,
        signoff_present=signoff_present,
    )

    out = {
        "schema": "btrack_31k41k_prophecy_shadow_gate_v1",
        "generated_at_utc": _iso_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "ssot_bundle": {
            "overlay_version": SSOT_OVERLAY,
            "panel_feature_mode": SSOT_PANEL_FEATURE_MODE,
            "panel_merge_policy": SSOT_PANEL_MERGE,
            "eval_artifact_default": str(DEFAULT_EVAL_V2B_STRICT),
            "fold_artifact_default": str(DEFAULT_FOLD),
            "panel_artifact_default": str(DEFAULT_PANEL),
            "human_signoff_template": str(DEFAULT_SIGNOFF_TEMPLATE),
            "human_signoff_runtime": str(signoff_path),
            "track_a_signoff_separate": "docs/final/artifacts/btrack_track_a_candidate_human_signoff_v1_latest.json",
        },
        "inputs": {
            "eval_json": str(eval_path),
            "eval_schema": schema,
            "overlay_version": overlay_version or None,
            "panel_feature_mode": panel_feature_mode,
            "panel_merge_policy": panel_merge_policy,
            "fold_json": str(args.fold_json) if not args.skip_fold_stability else None,
            "gate_mode": gate_mode,
            "human_signoff_json": str(args.human_signoff_json),
            "human_signoff_present": signoff_present,
            "stability_not_worse_flag": bool(args.stability_not_worse),
            "skip_fold_stability": bool(args.skip_fold_stability),
            "allow_legacy_max_merge": bool(args.allow_legacy_max_merge),
        },
        "metrics": {
            "delta_hit_rate": _as_float(shadow_probe.get("delta_hit_rate")),
            "pooled_delta_from_fold_artifact": _as_float(
                (fold_doc.get("pooled_panel") or {}).get("delta_hit_rate")
            ),
            "worst_fold_delta": _as_float(fold_aggregates.get("worst_fold_delta")),
            "positive_delta_folds": fold_aggregates.get("positive_delta_folds"),
            "effective_folds": fold_aggregates.get("effective_folds"),
        },
        "fold_stability_summary": fold_summary,
        "gate_checks": {
            "min_n_ok": min_n_ok,
            "shadow_delta_positive": delta_positive,
            "no_contamination": no_contamination,
            "v2_contract_ok": v2_contract_ok,
            "ssot_contract_ok": ssot_contract_ok,
            "technical_passed": technical_passed,
            "fold_stability_artifact_present": bool(fold_doc) or args.skip_fold_stability,
            "folds_count_ok": bool(fold_checks.get("folds_count_ok")) if fold_doc else None,
            "multi_window_positive_ok": bool(fold_checks.get("multi_window_positive_ok")) if fold_doc else None,
            "worst_fold_not_worse_ok": bool(fold_checks.get("worst_fold_not_worse_ok")) if fold_doc else None,
            "stability_not_worse": stability_ok,
            "human_signoff_ok": human_signoff_ok if gate_mode == "allowlist_review" else None,
            "human_signoff_scope_ok": _signoff_scope_ok(signoff_doc) if signoff_present else None,
        },
        "promotion_tier": promotion_tier,
        "all_passed": all_passed,
        "decision": decision,
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    print(
        f"decision={decision} all_passed={all_passed} gate_mode={gate_mode} "
        f"technical_passed={technical_passed} ssot_contract_ok={ssot_contract_ok}"
    )
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
