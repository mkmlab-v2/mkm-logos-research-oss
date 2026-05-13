"""Contract tests for Aramaic MVP audit tail streak alert."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "alert_aramaic_mvp_trend_v1.py"


def test_alert_critical_streak(tmp_path: Path) -> None:
    audit = tmp_path / "audit.jsonl"
    trend = tmp_path / "trend.json"
    out = tmp_path / "alert.json"
    rows = [
        {"run_at_utc": "2026-05-13T10:00:00Z", "conflict_ratio": 0.05},
        {"run_at_utc": "2026-05-13T11:00:00Z", "conflict_ratio": 0.35},
        {"run_at_utc": "2026-05-13T12:00:00Z", "conflict_ratio": 0.36},
        {"run_at_utc": "2026-05-13T13:00:00Z", "conflict_ratio": 0.37},
    ]
    audit.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    trend.write_text(json.dumps({"schema": "aramaic_mvp_audit_trend_v1", "generated_at_utc": "x"}), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--audit-jsonl",
            str(audit),
            "--trend-json",
            str(trend),
            "--output-json",
            str(out),
            "--window",
            "20",
            "--streak-min",
            "3",
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data.get("schema") == "aramaic_mvp_trend_alert_v1"
    assert data.get("severity") == "critical"
    assert data.get("streak", {}).get("length") == 3
    assert data.get("streak", {}).get("max_level_in_streak") == 2
    assert (data.get("webhook") or {}).get("status") == "skipped_dry_run"


def test_alert_ok_short_streak(tmp_path: Path) -> None:
    audit = tmp_path / "a2.jsonl"
    out = tmp_path / "a2out.json"
    rows = [
        {"run_at_utc": "2026-05-13T10:00:00Z", "conflict_ratio": 0.2},
        {"run_at_utc": "2026-05-13T11:00:00Z", "conflict_ratio": 0.2},
    ]
    audit.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--audit-jsonl",
            str(audit),
            "--output-json",
            str(out),
            "--streak-min",
            "3",
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data.get("severity") == "ok"
    assert (data.get("streak") or {}).get("length") == 2


def test_alert_empty_audit(tmp_path: Path) -> None:
    audit = tmp_path / "empty.jsonl"
    audit.write_text("", encoding="utf-8")
    out = tmp_path / "empty_alert.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--audit-jsonl", str(audit), "--output-json", str(out), "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data.get("severity") == "ok"
    assert (data.get("streak") or {}).get("length") == 0
