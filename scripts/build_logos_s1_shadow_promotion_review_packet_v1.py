#!/usr/bin/env python3
"""Aggregate Logos S1_SHADOW artifacts into one human-review packet (JSON + MD)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_GATE = ART / "logos_shadow_weekly_gate_latest.json"
DEFAULT_GATE_BOOT = ART / "logos_shadow_weekly_gate_bootstrap_latest.json"
DEFAULT_TREND = ART / "logos_shadow_weekly_trend_report_latest.json"
DEFAULT_ALERT = ART / "logos_shadow_alert_decision_latest.json"
DEFAULT_KPI = ART / "logos_shadow_promotion_kpi_progress_latest.json"
DEFAULT_INSIGHT = ART / "logos_shadow_insight_latest.json"
DEFAULT_RESONANCE = ART / "logos_regime_resonance_shadow_signal_latest.json"
DEFAULT_POLICY_CHECK = ART / "logos_response_policy_check_latest.json"
DEFAULT_CONSTITUTION = ROOT / "docs" / "final" / "CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md"
DEFAULT_OP_RULE = ART / "LOGOS_SHADOW_WEEKLY_GATE_OPERATION_RULE_V1.md"
DEFAULT_RESPONSE_POLICY = ART / "LOGOS_RESPONSE_POLICY_INTERNAL_EXTERNAL_V1.md"
DEFAULT_OUT_JSON = ART / "logos_s1_shadow_promotion_review_packet_latest.json"
DEFAULT_OUT_MD = ART / "logos_s1_shadow_promotion_review_packet_latest.md"
DEFAULT_HUMAN_APPROVAL = ART / "logos_s1_shadow_promotion_human_approval_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return _read_json(path)


def _rel_to_root(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build Logos S1_SHADOW promotion review packet (evidence pointers + KPI snapshot)."
    )
    ap.add_argument("--weekly-gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--weekly-gate-bootstrap-json", type=Path, default=DEFAULT_GATE_BOOT)
    ap.add_argument("--weekly-trend-json", type=Path, default=DEFAULT_TREND)
    ap.add_argument("--alert-json", type=Path, default=DEFAULT_ALERT)
    ap.add_argument("--kpi-progress-json", type=Path, default=DEFAULT_KPI)
    ap.add_argument("--insight-json", type=Path, default=DEFAULT_INSIGHT)
    ap.add_argument("--resonance-json", type=Path, default=DEFAULT_RESONANCE)
    ap.add_argument("--response-policy-check-json", type=Path, default=DEFAULT_POLICY_CHECK)
    ap.add_argument("--constitution-md", type=Path, default=DEFAULT_CONSTITUTION)
    ap.add_argument("--operation-rule-md", type=Path, default=DEFAULT_OP_RULE)
    ap.add_argument("--response-policy-md", type=Path, default=DEFAULT_RESPONSE_POLICY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--output-md", type=Path, default=DEFAULT_OUT_MD)
    args = ap.parse_args()

    def resolve(p: Path) -> Path:
        return p if p.is_absolute() else ROOT / p

    gate_path = resolve(args.weekly_gate_json)
    boot_path = resolve(args.weekly_gate_bootstrap_json)
    trend_path = resolve(args.weekly_trend_json)
    alert_path = resolve(args.alert_json)
    kpi_path = resolve(args.kpi_progress_json)
    insight_path = resolve(args.insight_json)
    resonance_path = resolve(args.resonance_json)
    policy_check_path = resolve(args.response_policy_check_json)
    constitution_path = resolve(args.constitution_md)
    op_rule_path = resolve(args.operation_rule_md)
    resp_policy_path = resolve(args.response_policy_md)
    out_json = resolve(args.output_json)
    out_md = resolve(args.output_md)

    for req in (gate_path, trend_path, alert_path, kpi_path):
        if not req.is_file():
            raise SystemExit(f"Missing required json: {req}")

    gate = _read_json(gate_path)
    boot = _read_json_optional(boot_path)
    trend = _read_json(trend_path)
    alert = _read_json(alert_path)
    kpi = _read_json(kpi_path)
    insight = _read_json_optional(insight_path)
    resonance = _read_json_optional(resonance_path)
    policy_check = _read_json_optional(policy_check_path)

    human_approval_path = DEFAULT_HUMAN_APPROVAL
    human_approval = _read_json_optional(human_approval_path)
    gm = gate.get("metrics") or {}
    tm = trend.get("summary") or {}
    summ = insight.get("summary") or {}

    summary = {
        "strict_weekly_gate": {
            "decision": gate.get("decision"),
            "samples": gm.get("samples"),
            "mean_top1_cosine_7d": gm.get("mean_top1_cosine_7d"),
            "low_confidence_rate_7d": gm.get("low_confidence_rate_7d"),
            "query_error_rate_7d": gm.get("query_error_rate_7d"),
        },
        "bootstrap_weekly_gate": {
            "decision": boot.get("decision"),
            "samples": ((boot.get("metrics") or {}).get("samples")),
        },
        "weekly_trend": {
            "samples": trend.get("samples"),
            "mean_top1_cosine_7d_avg": tm.get("mean_top1_cosine_7d_avg"),
            "query_error_rate_7d_aggregate": tm.get("query_error_rate_7d_aggregate"),
            "low_conf_rate_7d_avg": tm.get("low_conf_rate_7d_avg"),
        },
        "alert": {
            "should_alert": ((alert.get("alert") or {}).get("should_alert")),
            "reason": ((alert.get("alert") or {}).get("reason")),
        },
        "kpi_contract": {
            "status": kpi.get("status"),
            "passed": kpi.get("passed"),
            "checks": kpi.get("checks"),
            "consecutive_strict_go_windows": kpi.get("consecutive_strict_go_windows"),
        },
        "shadow_insight": {
            "decision": summ.get("decision"),
            "mean_top1_cosine": summ.get("mean_top1_cosine"),
            "queries_ok": summ.get("queries_ok"),
            "queries_error": summ.get("queries_error"),
        },
        "regime_resonance_shadow": {
            "status": resonance.get("status"),
            "best_regime": ((resonance.get("summary") or {}).get("best_regime")),
            "best_top_hit_cosine": ((resonance.get("summary") or {}).get("best_top_hit_cosine")),
        },
        "response_policy_check": {
            "status": policy_check.get("status"),
            "passed": policy_check.get("passed"),
        },
    }

    packet: dict[str, Any] = {
        "schema": "logos_s1_shadow_promotion_review_packet_v1",
        "generated_at_utc": _now(),
        "purpose": "Human promotion review snapshot — pointers and KPI summary only; does not enable A-track or live trading.",
        "constitution_pointer": {
            "path": _rel_to_root(constitution_path, ROOT),
            "section": "Promotion Loop — Logos S1_SHADOW (section 8.2)",
            "exists": constitution_path.is_file(),
        },
        "policy_documents": {
            "weekly_gate_operation_rule": _rel_to_root(op_rule_path, ROOT),
            "response_policy_internal_external": _rel_to_root(resp_policy_path, ROOT),
            "operation_rule_exists": op_rule_path.is_file(),
            "response_policy_exists": resp_policy_path.is_file(),
        },
        "summary": summary,
        "track_wall": {
            "shadow_only": True,
            "promotion_to_a_track_allowed": False,
            "auto_trade_enable": False,
            "human_review_required": True,
        },
        "human_review_fields": [
            "reviewer_id_or_initials",
            "review_timestamp_utc",
            "decision (HOLD_CONTINUE_SHADOW | ACK_READY_FOR_NEXT_STAGE_PLANNING)",
            "notes",
        ],
        "regression_bundle": {
            "pytest_commands": [
                "py -m pytest tests/test_promote_logos_to_shadow_live_v1.py tests/test_build_logos_shadow_alert_decision_v1.py -q --tb=short",
                "py -m pytest tests/test_build_logos_s1_shadow_promotion_review_packet_v1.py -q --tb=short",
                "py -m pytest tests/test_record_logos_s1_shadow_promotion_human_approval_v1.py -q --tb=short",
            ],
        },
        "evidence_paths": {
            "weekly_gate_json": str(gate_path.resolve()),
            "weekly_gate_bootstrap_json": str(boot_path.resolve()) if boot_path.is_file() else "",
            "weekly_trend_json": str(trend_path.resolve()),
            "alert_json": str(alert_path.resolve()),
            "kpi_progress_json": str(kpi_path.resolve()),
            "insight_json": str(insight_path.resolve()) if insight_path.is_file() else "",
            "resonance_shadow_json": str(resonance_path.resolve()) if resonance_path.is_file() else "",
            "response_policy_check_json": str(policy_check_path.resolve()) if policy_check_path.is_file() else "",
            "review_packet_json": str(out_json.resolve()),
            "review_packet_md": str(out_md.resolve()),
        },
    }

    if human_approval:
        packet["human_approval_record"] = {
            "present": True,
            "generated_at_utc": human_approval.get("generated_at_utc"),
            "decision": human_approval.get("decision"),
            "reviewer_label": human_approval.get("reviewer_label"),
            "schema": human_approval.get("schema"),
        }
        packet["evidence_paths"]["human_approval_json"] = str(human_approval_path.resolve())
    else:
        packet["human_approval_record"] = {"present": False}

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Logos S1_SHADOW — Promotion review packet",
        "",
        f"- generated_at_utc: `{packet['generated_at_utc']}`",
        f"- kpi_contract_status: `{summary['kpi_contract'].get('status')}`",
        f"- kpi_contract_passed: `{summary['kpi_contract'].get('passed')}`",
        f"- strict_gate: `{summary['strict_weekly_gate'].get('decision')}` (samples={summary['strict_weekly_gate'].get('samples')})",
        f"- bootstrap_gate: `{summary['bootstrap_weekly_gate'].get('decision')}`",
        f"- alert_should_alert: `{summary['alert'].get('should_alert')}`",
        f"- response_policy_check: `{summary['response_policy_check'].get('status')}`",
        f"- resonance_shadow: `{summary['regime_resonance_shadow'].get('status')}`",
        "",
    ]
    if human_approval:
        md_lines.extend(
            [
                "## Human approval (recorded)",
                f"- generated_at_utc: `{human_approval.get('generated_at_utc')}`",
                f"- decision: `{human_approval.get('decision')}`",
                f"- reviewer_label: `{human_approval.get('reviewer_label')}`",
                f"- artifact: `{human_approval_path.resolve()}`",
                "",
            ]
        )
    else:
        md_lines.extend(
            [
                "## Human review (fill in)",
                "- reviewer: ",
                "- review_timestamp_utc: ",
                "- decision: HOLD_CONTINUE_SHADOW | ACK_READY_FOR_NEXT_STAGE_PLANNING",
                "- notes: ",
                "",
            ]
        )

    md_lines.extend(
        [
        "## Evidence (JSON)",
        f"- `{packet['evidence_paths']['review_packet_json']}`",
        "",
        "## Constitution",
        f"- `{packet['constitution_pointer']['path']}` — {packet['constitution_pointer']['section']}",
        "",
        "## Regression",
        ]
    )
    for cmd in packet["regression_bundle"]["pytest_commands"]:
        md_lines.append(f"- `{cmd}`")
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "out_json": str(out_json), "out_md": str(out_md)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
