"""Contract tests for Aramaic MVP audit log trend reporter."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "report_aramaic_mvp_audit_trend_v1.py"


def test_report_audit_trend_cli_writes_schema(tmp_path: Path) -> None:
    audit = tmp_path / "audit.jsonl"
    out = tmp_path / "trend.json"
    rows = [
        {
            "run_at_utc": "2026-05-13T10:00:00Z",
            "shift_score": 0.5,
            "delta_shift_score": 0.01,
            "oos_shift_score": 0.52,
            "oos_delta_shift_score": 0.02,
            "conflict_ratio": 0.1,
            "insight_cap_bucket": "mid",
            "oos_scenario": "neutral",
        },
        {
            "run_at_utc": "2026-05-13T11:00:00Z",
            "shift_score": 0.6,
            "delta_shift_score": 0.02,
            "oos_shift_score": 0.55,
            "oos_delta_shift_score": 0.03,
            "conflict_ratio": 0.15,
            "insight_cap_bucket": "high",
            "oos_scenario": "stress_tilt",
        },
        {
            "run_at_utc": "2026-05-13T12:00:00Z",
            "shift_score": 0.55,
            "delta_shift_score": 0.015,
            "oos_shift_score": 0.53,
            "oos_delta_shift_score": 0.025,
            "conflict_ratio": 0.12,
            "insight_cap_bucket": "mid",
            "oos_scenario": "neutral",
        },
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
            "--window",
            "10",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data.get("schema") == "aramaic_mvp_audit_trend_v1"
    assert data.get("research_only") is True
    assert data.get("source_track") == "B"
    w = data.get("window") or {}
    assert w.get("n_used") == 3
    m = data.get("metrics") or {}
    assert m.get("shift_score", {}).get("mean") == pytest.approx(0.55, rel=1e-6)
    hist = data.get("insight_cap_bucket_histogram") or {}
    assert hist.get("mid") == 2
    assert hist.get("high") == 1


def test_report_audit_trend_empty_log(tmp_path: Path) -> None:
    audit = tmp_path / "empty.jsonl"
    audit.write_text("", encoding="utf-8")
    out = tmp_path / "empty_trend.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--audit-jsonl", str(audit), "--output-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data.get("window", {}).get("n_used") == 0
    assert (data.get("metrics") or {}).get("shift_score") is None
