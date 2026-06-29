from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "alert_general_prophecy_holdout_gate_v1.py"


def test_holdout_alert_warn_dry_run(tmp_path: Path):
    gate = tmp_path / "gate_warn.json"
    out = tmp_path / "alert_result.json"
    gate.write_text(
        json.dumps(
            {
                "schema": "general_prophecy_explainability_holdout_gate_v1",
                "decision": "WARN_HOLDOUT_DRIFT_RISK",
                "all_pass": False,
                "profile": "ops",
                "thresholds": {"min_holdout_direct_rate": 0.85},
                "metrics_snapshot": {"holdout_direct_match_rate": 0.7},
                "checks": {
                    "min_holdout_questions_pass": True,
                    "min_holdout_direct_rate_pass": False,
                    "min_holdout_repro_rate_pass": False,
                    "min_holdout_coverage_pass": True,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--gate-json",
            str(gate),
            "--output-json",
            str(out),
            "--webhook-url",
            "https://example.invalid/webhook",
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["alert_needed"] is True
    assert doc["dispatch_result"] == "dry_run"
    assert doc["failed_check_keys"] == [
        "min_holdout_direct_rate_pass",
        "min_holdout_repro_rate_pass",
    ]


def test_holdout_alert_slack_payload_wraps_text():
    from scripts.alert_general_prophecy_holdout_gate_v1 import _slack_webhook_body

    payload = {
        "decision": "WARN_HOLDOUT_DRIFT_RISK",
        "all_pass": False,
        "profile": "research",
        "failed_check_keys": ["min_holdout_repro_rate_pass"],
        "metrics_snapshot": {
            "holdout_reproducible_evidence_rate": 0.68,
            "holdout_avg_biblical_keyword_coverage": 0.29,
        },
    }
    body = json.loads(
        _slack_webhook_body("https://hooks.slack.com/services/T00/B00/xxx", payload).decode("utf-8")
    )
    assert isinstance(body.get("text"), str)
    assert "WARN_HOLDOUT_DRIFT_RISK" in body["text"]
    generic = json.loads(
        _slack_webhook_body("https://example.invalid/webhook", payload).decode("utf-8")
    )
    assert generic["decision"] == "WARN_HOLDOUT_DRIFT_RISK"


def test_holdout_alert_not_needed(tmp_path: Path):
    gate = tmp_path / "gate_ok.json"
    out = tmp_path / "alert_result_ok.json"
    gate.write_text(
        json.dumps(
            {
                "schema": "general_prophecy_explainability_holdout_gate_v1",
                "decision": "GO_HOLDOUT_STABLE",
                "all_pass": True,
                "checks": {"min_holdout_direct_rate_pass": True},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--gate-json",
            str(gate),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["alert_needed"] is False
    assert doc["dispatch_result"] == "not_needed"
    assert doc["failed_check_keys"] == []
