from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "alert_btrack_automation_health_v1.py"


def _write_snapshot(path: Path, ops_ready: bool) -> None:
    payload = {
        "schema": "btrack_automation_health_snapshot_v1",
        "generated_at_utc": "2026-04-25T00:00:00Z",
        "summary": {
            "all_tasks_ok": ops_ready,
            "all_artifacts_ok": ops_ready,
            "ops_ready": ops_ready,
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_alert_returns_zero_when_ops_ready(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.json"
    out = tmp_path / "alert.json"
    _write_snapshot(snapshot, ops_ready=True)

    run = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--snapshot-json",
            str(snapshot),
            "--out",
            str(out),
            "--always-log",
        ],
        cwd=str(ROOT),
    )
    assert run.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["status"] == "ok"
    assert doc["ops_ready"] is True
    assert doc["alert_sent"] is False


def test_alert_returns_nonzero_when_not_ready_without_webhook(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.json"
    out = tmp_path / "alert.json"
    _write_snapshot(snapshot, ops_ready=False)

    env = os.environ.copy()
    env.pop("OPS_ALARM_WEBHOOK_URL", None)
    env.pop("COMPRESSION_KPI_ALARM_WEBHOOK_URL", None)

    run = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--snapshot-json",
            str(snapshot),
            "--out",
            str(out),
            "--always-log",
        ],
        cwd=str(ROOT),
        env=env,
    )
    assert run.returncode == 1
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["status"] == "alert"
    assert doc["ops_ready"] is False
    assert doc["alert_sent"] is False
    assert doc.get("alert_skipped_reason") == "webhook_not_configured"
