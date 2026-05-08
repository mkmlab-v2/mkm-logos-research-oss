#!/usr/bin/env python3
"""Evaluate GO/WATCH/HOLD from 3-lens normalized feature vector."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs" / "final" / "artifacts" / "three_lens_fusion_coordinator_v1_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "three_lens_feature_gate_v2_latest.json"
DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "three_lens_staged_inclusion_policy_v1.json"
DEFAULT_SHADOW_HISTORY = ROOT / "docs" / "final" / "artifacts" / "three_lens_shadow_history_v1.jsonl"
DEFAULT_EXTERNAL_INTEL = ROOT / "docs" / "final" / "artifacts" / "three_lens_external_intel_snapshot_latest.json"
DEFAULT_CONDITIONAL_GO_POLICY = ROOT / "docs" / "final" / "artifacts" / "conditional_go_policy_v1.json"
DEFAULT_CONDITIONAL_GO_MARKET = ROOT / "docs" / "final" / "artifacts" / "conditional_go_market_check_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return _read_json(path)


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-json", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--hold-risk-cut", type=float, default=0.75)
    ap.add_argument("--watch-risk-cut", type=float, default=0.58)
    ap.add_argument("--go-opportunity-cut", type=float, default=0.62)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--shadow-history-jsonl", type=Path, default=DEFAULT_SHADOW_HISTORY)
    ap.add_argument("--external-intel-json", type=Path, default=DEFAULT_EXTERNAL_INTEL)
    ap.add_argument("--require-external-intel", action="store_true")
    ap.add_argument("--conditional-go-policy-json", type=Path, default=DEFAULT_CONDITIONAL_GO_POLICY)
    ap.add_argument("--conditional-go-market-json", type=Path, default=DEFAULT_CONDITIONAL_GO_MARKET)
    ap.add_argument("--watch-bias-lookback", type=int, default=14)
    ap.add_argument("--watch-bias-threshold", type=float, default=0.85)
    args = ap.parse_args()

    in_path = args.input_json if args.input_json.is_absolute() else ROOT / args.input_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    policy_path = args.policy_json if args.policy_json.is_absolute() else ROOT / args.policy_json
    shadow_history_path = args.shadow_history_jsonl if args.shadow_history_jsonl.is_absolute() else ROOT / args.shadow_history_jsonl
    external_intel_path = args.external_intel_json if args.external_intel_json.is_absolute() else ROOT / args.external_intel_json
    conditional_go_policy_path = (
        args.conditional_go_policy_json if args.conditional_go_policy_json.is_absolute() else ROOT / args.conditional_go_policy_json
    )
    conditional_go_market_path = (
        args.conditional_go_market_json if args.conditional_go_market_json.is_absolute() else ROOT / args.conditional_go_market_json
    )
    if not in_path.is_file():
        raise SystemExit(f"Missing input: {in_path}")

    doc = _read_json(in_path)
    fusion = doc.get("fusion") if isinstance(doc.get("fusion"), dict) else {}
    vec = fusion.get("common_feature_vector_v1") if isinstance(fusion.get("common_feature_vector_v1"), dict) else {}
    coord = doc.get("coordinator") if isinstance(doc.get("coordinator"), dict) else {}
    source_action = str(coord.get("action") or "WATCH").upper()

    required_keys = (
        "sasang_stress_score_0_1",
        "myeongni_direction_score_0_1",
        "myeongni_confidence_score_0_1",
        "logos_tension_score_0_1",
    )
    missing = [k for k in required_keys if k not in vec]

    sasang_stress = _f(vec.get("sasang_stress_score_0_1"))
    myeongni_dir = _f(vec.get("myeongni_direction_score_0_1"))
    myeongni_conf = _f(vec.get("myeongni_confidence_score_0_1"))
    logos_tension = _f(vec.get("logos_tension_score_0_1"))
    chronicle_signal = vec.get("chronicle_signal_score_0_1")
    chronicle_score = 0.5 if chronicle_signal is None else _f(chronicle_signal, 0.5)
    chronicle_ptrs = vec.get("chronicle_evidence_pointers") if isinstance(vec.get("chronicle_evidence_pointers"), list) else []
    policy = _read_json(policy_path) if policy_path.is_file() else {}
    feature_rows = policy.get("features") if isinstance(policy.get("features"), list) else []
    feature_status = {
        str(r.get("id")): str(r.get("status") or "shadow").lower()
        for r in feature_rows
        if isinstance(r, dict) and r.get("id")
    }
    chronicle_enabled = feature_status.get("chronicle_weekly_eval_signal", "enabled") == "enabled"
    chronicle_weight = 0.4 if chronicle_enabled else 0.0
    myeongni_weight = 1.0 - chronicle_weight

    risk_score = max(0.0, min(1.0, 0.45 * sasang_stress + 0.35 * logos_tension + 0.20 * (1.0 - myeongni_conf)))
    opportunity_score = max(0.0, min(1.0, myeongni_weight * myeongni_dir + chronicle_weight * chronicle_score))

    weekly_eval_bound = any("chronicle_history_news_signal_weekly_eval_latest.json" in str(p) for p in chronicle_ptrs)
    logos_non_gating_ok = bool(fusion.get("logos_non_gating_ok") is True)

    shadow_tail = _read_jsonl(shadow_history_path)
    if args.watch_bias_lookback > 0:
        shadow_tail = shadow_tail[-args.watch_bias_lookback :]
    watch_count = sum(1 for r in shadow_tail if str(r.get("action") or "").upper() == "WATCH")
    watch_bias_ratio = (watch_count / len(shadow_tail)) if shadow_tail else 0.0
    watch_bias_relief_eligible = (
        len(shadow_tail) >= 7
        and watch_bias_ratio >= args.watch_bias_threshold
        and weekly_eval_bound
        and risk_score <= 0.40
        and opportunity_score >= 0.42
    )
    external_intel = _read_json(external_intel_path) if external_intel_path.is_file() else {}
    external_news = external_intel.get("external_news") if isinstance(external_intel.get("external_news"), dict) else {}
    external_ready = bool(external_intel.get("ready_for_orchestrator_context") is True)
    external_news_items = int(external_news.get("items_count") or 0)
    external_news_effective_items = int(external_news.get("effective_items_count") or external_news_items)
    external_intel_guard_failed = bool(args.require_external_intel and (not external_ready or external_news_effective_items <= 0))
    conditional_go_policy = _read_json_optional(conditional_go_policy_path)
    conditional_go_market = _read_json_optional(conditional_go_market_path)
    conditional_go_enabled = (
        conditional_go_policy.get("schema") == "conditional_go_policy_v1"
        and str(conditional_go_policy.get("mode") or "") == "LOCKED_MODE_WITH_RECON_SLOT"
    )
    activation = conditional_go_market.get("activation") if isinstance(conditional_go_market.get("activation"), dict) else {}
    activation_all_met = bool(activation.get("all_conditions_met") is True)
    activation_conf = _f(activation.get("confidence_0_1"), 0.0)
    activation_min_conf = _f(
        ((conditional_go_policy.get("activation") or {}).get("min_confidence_0_1")),
        0.62,
    )
    conditional_go_armed = bool(conditional_go_enabled and activation_all_met and activation_conf >= activation_min_conf)
    allocation = conditional_go_policy.get("allocation") if isinstance(conditional_go_policy.get("allocation"), dict) else {}
    recon_slot_min_pct = _f(allocation.get("recon_slot_min_pct"), 0.10)
    recon_slot_max_pct = _f(allocation.get("recon_slot_max_pct"), 0.20)

    if missing:
        action = "HOLD"
        reason = "missing_common_feature_keys"
    elif not logos_non_gating_ok:
        action = "HOLD"
        reason = "logos_non_gating_violation"
    elif source_action in {"REDUCE", "HOLD"} and risk_score >= args.watch_risk_cut:
        action = "HOLD"
        reason = "source_action_risk_cap"
    elif risk_score >= args.hold_risk_cut:
        action = "HOLD"
        reason = "risk_score_above_hold_cut"
    elif external_intel_guard_failed:
        action = "WATCH"
        reason = "stale_external_intel"
    elif opportunity_score >= args.go_opportunity_cut and risk_score <= args.watch_risk_cut and weekly_eval_bound:
        action = "GO"
        reason = "opportunity_pass_with_weekly_eval_evidence"
    elif watch_bias_relief_eligible:
        action = "GO"
        reason = "watch_bias_relief_low_risk_band"
    else:
        action = "WATCH"
        reason = "default_watch_band"
    if conditional_go_enabled and action == "GO" and source_action == "GO":
        if conditional_go_armed:
            reason = "conditional_go_activation_pass"
        else:
            action = "WATCH"
            reason = "conditional_go_not_armed"

    payload = {
        "schema": "three_lens_feature_gate_v2",
        "generated_at_utc": _now(),
        "input_json": str(in_path),
        "policy_json": str(policy_path),
        "thresholds": {
            "hold_risk_cut": args.hold_risk_cut,
            "watch_risk_cut": args.watch_risk_cut,
            "go_opportunity_cut": args.go_opportunity_cut,
        },
        "metrics": {
            "risk_score_0_1": round(risk_score, 6),
            "opportunity_score_0_1": round(opportunity_score, 6),
            "weekly_eval_evidence_bound": weekly_eval_bound,
            "chronicle_enabled_by_policy": chronicle_enabled,
            "logos_non_gating_ok": logos_non_gating_ok,
            "source_action": source_action,
            "watch_bias_ratio": round(watch_bias_ratio, 6),
            "watch_bias_relief_eligible": watch_bias_relief_eligible,
            "external_intel_ready": external_ready,
            "external_news_items_count": external_news_items,
            "external_news_effective_items_count": external_news_effective_items,
            "external_intel_guard_failed": external_intel_guard_failed,
            "conditional_go_enabled": conditional_go_enabled,
            "conditional_go_armed": conditional_go_armed,
        },
        "feature_status": feature_status,
        "conditional_go": {
            "policy_json": str(conditional_go_policy_path),
            "market_check_json": str(conditional_go_market_path),
            "activation_all_conditions_met": activation_all_met,
            "activation_confidence_0_1": round(activation_conf, 6),
            "activation_min_confidence_0_1": round(activation_min_conf, 6),
            "recon_slot_min_pct": round(recon_slot_min_pct, 6),
            "recon_slot_max_pct": round(recon_slot_max_pct, 6),
        },
        "watch_bias_control": {
            "shadow_history_jsonl": str(shadow_history_path),
            "lookback": args.watch_bias_lookback,
            "watch_bias_threshold": args.watch_bias_threshold,
            "shadow_history_count": len(shadow_tail),
        },
        "decision": {
            "action": action,
            "reason": reason,
            "human_signoff_required": True,
            "research_only": True,
        },
        "missing_keys": missing,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "action": action}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
