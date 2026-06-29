# Purpose: Clinician graph pilot KPI report aggregates feedback + telemetry.
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_clinician_graph_pilot_kpi_report_v1_smoke(tmp_path: Path) -> None:
    feedback = tmp_path / "feedback.jsonl"
    telemetry = tmp_path / "telemetry.jsonl"
    out = tmp_path / "kpi.json"

    feedback.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "schema": "clinician_graph_review_feedback_event_v1",
                        "ts": "2026-06-25T12:00:00Z",
                        "encounter_ref": "req-demo-001",
                        "target_id": "node:a",
                        "target_kind": "node",
                        "feedback": "up",
                        "reason_code": None,
                    }
                ),
                json.dumps(
                    {
                        "schema": "clinician_graph_review_feedback_event_v1",
                        "ts": "2026-06-25T12:05:00Z",
                        "encounter_ref": "req-demo-001",
                        "target_id": "signoff:req-demo-001",
                        "target_kind": "node",
                        "feedback": "up",
                        "reason_code": "physician_signoff_checklist",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    telemetry.write_text(
        json.dumps(
            {
                "event": "clinician_graph_build_v1",
                "ts_utc": "2026-06-25T12:01:00Z",
                "encounter_ref": "req-demo-001",
                "node_count": 5,
            }
        )
        + "\n"
        + json.dumps(
            {
                "event": "clinician_graph_review_timing_v1",
                "ts_utc": "2026-06-25T12:06:00Z",
                "encounter_ref": "req-demo-001",
                "duration_since_cds_ready_ms": 360000,
                "duration_since_graph_build_ms": 120000,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_clinician_graph_pilot_kpi_report_v1.py"),
            "--feedback-jsonl",
            str(feedback),
            "--telemetry-jsonl",
            str(telemetry),
            "--out-json",
            str(out),
            "--window-days",
            "30",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "clinician_graph_pilot_kpi_summary_v1"
    assert doc["feedback"]["counts"]["up"] == 2
    assert doc["feedback"]["signoff_count"] == 1
    assert doc["telemetry"]["event_counts"]["clinician_graph_build_v1"] == 1
    assert doc["kpi_headline"]["physician_approval_rate"] == 1.0
