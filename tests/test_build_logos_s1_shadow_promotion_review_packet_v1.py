from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_s1_shadow_promotion_review_packet_v1.py"


def test_review_packet_builds_json_md(tmp_path: Path) -> None:
    gate = tmp_path / "gate.json"
    trend = tmp_path / "trend.json"
    alert = tmp_path / "alert.json"
    kpi = tmp_path / "kpi.json"
    boot = tmp_path / "boot.json"
    insight = tmp_path / "insight.json"
    resonance = tmp_path / "resonance.json"
    policy_check = tmp_path / "policy_check.json"
    out_json = tmp_path / "packet.json"
    out_md = tmp_path / "packet.md"

    gate.write_text(
        json.dumps(
            {
                "schema": "logos_shadow_weekly_gate_v1",
                "decision": "GO",
                "metrics": {
                    "samples": 8,
                    "mean_top1_cosine_7d": 0.11,
                    "low_confidence_rate_7d": 0.0,
                    "query_error_rate_7d": 0.0,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    trend.write_text(
        json.dumps(
            {
                "schema": "logos_shadow_weekly_trend_report_v1",
                "samples": 8,
                "summary": {
                    "mean_top1_cosine_7d_avg": 0.11,
                    "query_error_rate_7d_aggregate": 0.0,
                    "low_conf_rate_7d_avg": 0.0,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    alert.write_text(
        json.dumps(
            {
                "schema": "logos_shadow_alert_decision_v1",
                "alert": {"should_alert": False, "reason": "no_alert_rule_match"},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    kpi.write_text(
        json.dumps(
            {
                "schema": "logos_shadow_promotion_kpi_progress_v1",
                "status": "READY_FOR_REVIEW",
                "passed": True,
                "checks": {"strict_go_consecutive_2w": True},
                "consecutive_strict_go_windows": 3,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    boot.write_text(
        json.dumps({"schema": "logos_shadow_weekly_gate_v1", "decision": "GO", "metrics": {"samples": 8}}),
        encoding="utf-8",
    )
    insight.write_text(
        json.dumps(
            {
                "summary": {
                    "decision": "GO",
                    "mean_top1_cosine": 0.1,
                    "queries_ok": 12,
                    "queries_error": 0,
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    resonance.write_text(
        json.dumps(
            {
                "status": "OK",
                "summary": {"best_regime": "covid", "best_top_hit_cosine": 0.88},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    policy_check.write_text(
        json.dumps({"schema": "logos_response_policy_check_v1", "status": "OK", "passed": True}),
        encoding="utf-8",
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--weekly-gate-json",
            str(gate),
            "--weekly-gate-bootstrap-json",
            str(boot),
            "--weekly-trend-json",
            str(trend),
            "--alert-json",
            str(alert),
            "--kpi-progress-json",
            str(kpi),
            "--insight-json",
            str(insight),
            "--resonance-json",
            str(resonance),
            "--response-policy-check-json",
            str(policy_check),
            "--constitution-md",
            str(ROOT / "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md"),
            "--operation-rule-md",
            str(ROOT / "docs/final/artifacts/LOGOS_SHADOW_WEEKLY_GATE_OPERATION_RULE_V1.md"),
            "--response-policy-md",
            str(ROOT / "docs/final/artifacts/LOGOS_RESPONSE_POLICY_INTERNAL_EXTERNAL_V1.md"),
            "--output-json",
            str(out_json),
            "--output-md",
            str(out_md),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    assert out_json.is_file()
    assert out_md.is_file()

    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_s1_shadow_promotion_review_packet_v1"
    assert doc.get("summary", {}).get("kpi_contract", {}).get("status") == "READY_FOR_REVIEW"
    assert doc.get("track_wall", {}).get("human_review_required") is True
    cmds = doc["regression_bundle"]["pytest_commands"]
    assert any("test_build_logos_s1_shadow_promotion_review_packet_v1.py" in c for c in cmds)
    assert any("test_record_logos_s1_shadow_promotion_human_approval_v1.py" in c for c in cmds)
