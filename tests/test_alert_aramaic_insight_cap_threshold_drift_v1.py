"""Contract: alert_aramaic_insight_cap_threshold_drift_v1 compares last two recommended snapshots."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "alert_aramaic_insight_cap_threshold_drift_v1.py"

HISTORY_SCHEMA = "aramaic_insight_cap_bucket_threshold_history_row_v1"


def _row(rec: dict, ts: str) -> dict:
    return {
        "schema": HISTORY_SCHEMA,
        "recorded_at_utc": ts,
        "recommended": rec,
    }


def _run(
    hist: Path,
    out: Path,
    *,
    drift_threshold: str | None = None,
    extra_args: list[str] | None = None,
) -> dict:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--history-jsonl",
        str(hist),
        "--output-json",
        str(out),
    ]
    if drift_threshold is not None:
        cmd.extend(["--drift-threshold", drift_threshold])
    if extra_args:
        cmd.extend(extra_args)
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    return json.loads(out.read_text(encoding="utf-8"))


def test_drift_insufficient_history_empty(tmp_path: Path) -> None:
    hist = tmp_path / "h.jsonl"
    out = tmp_path / "a.json"
    hist.write_text("", encoding="utf-8")
    doc = _run(hist, out)
    assert doc["reason"] == "insufficient_history"
    assert doc["should_alert"] is False
    assert doc["history_recommended_snapshots"] == 0
    assert doc["webhook"]["status"] == "skipped_insufficient_history"


def test_drift_insufficient_history_one_snapshot(tmp_path: Path) -> None:
    hist = tmp_path / "h.jsonl"
    out = tmp_path / "a.json"
    rec = {"mid_vol_threshold": 0.2, "high_vol_threshold": 0.4}
    hist.write_text(json.dumps(_row(rec, "2026-01-01T00:00:00Z"), ensure_ascii=False) + "\n", encoding="utf-8")
    doc = _run(hist, out)
    assert doc["reason"] == "insufficient_history"
    assert doc["should_alert"] is False
    assert doc["webhook"]["status"] == "skipped_insufficient_history"


def test_drift_stable_below_threshold(tmp_path: Path) -> None:
    hist = tmp_path / "h.jsonl"
    out = tmp_path / "a.json"
    rec = {
        "mid_vol_threshold": 0.2,
        "high_vol_threshold": 0.4,
        "insight_max_delta_low_vol": 0.06,
        "insight_max_delta_mid_vol": 0.045,
        "insight_max_delta_high_vol": 0.03,
    }
    lines = [
        json.dumps(_row(rec, "2026-01-01T00:00:00Z"), ensure_ascii=False),
        json.dumps(_row(rec, "2026-01-02T00:00:00Z"), ensure_ascii=False),
    ]
    hist.write_text("\n".join(lines) + "\n", encoding="utf-8")
    doc = _run(hist, out, drift_threshold="1e-4")
    assert doc["reason"] == "stable_below_threshold"
    assert doc["should_alert"] is False
    assert doc["max_abs_delta"] == 0.0
    assert doc["webhook"]["status"] == "skipped_should_false"


def test_drift_threshold_crossing_alerts(tmp_path: Path) -> None:
    hist = tmp_path / "h.jsonl"
    out = tmp_path / "a.json"
    r1 = {
        "mid_vol_threshold": 0.2,
        "high_vol_threshold": 0.4,
        "insight_max_delta_low_vol": 0.06,
        "insight_max_delta_mid_vol": 0.045,
        "insight_max_delta_high_vol": 0.03,
    }
    r2 = dict(r1)
    r2["mid_vol_threshold"] = 0.35
    lines = [
        json.dumps(_row(r1, "2026-01-01T00:00:00Z"), ensure_ascii=False),
        json.dumps(_row(r2, "2026-01-02T00:00:00Z"), ensure_ascii=False),
    ]
    hist.write_text("\n".join(lines) + "\n", encoding="utf-8")
    doc = _run(hist, out, drift_threshold="0.01", extra_args=["--dry-run"])
    assert doc["reason"] == "threshold_drift"
    assert doc["should_alert"] is True
    assert "mid_vol_threshold" in doc["drifted_keys"]
    assert doc["max_abs_delta"] >= 0.14
    assert doc["webhook"]["status"] == "skipped_dry_run"
    assert doc["webhook"]["sent"] is False


def test_drift_threshold_without_dry_run_skips_when_no_webhook_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARAMAIC_INSIGHT_CAP_DRIFT_ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("OPS_ALARM_WEBHOOK_URL", raising=False)
    hist = tmp_path / "h2.jsonl"
    out = tmp_path / "a2.json"
    r1 = {
        "mid_vol_threshold": 0.2,
        "high_vol_threshold": 0.4,
        "insight_max_delta_low_vol": 0.06,
        "insight_max_delta_mid_vol": 0.045,
        "insight_max_delta_high_vol": 0.03,
    }
    r2 = dict(r1)
    r2["mid_vol_threshold"] = 0.35
    lines = [
        json.dumps(_row(r1, "2026-01-01T00:00:00Z"), ensure_ascii=False),
        json.dumps(_row(r2, "2026-01-02T00:00:00Z"), ensure_ascii=False),
    ]
    hist.write_text("\n".join(lines) + "\n", encoding="utf-8")
    doc = _run(hist, out, drift_threshold="0.01")
    assert doc["should_alert"] is True
    assert doc["webhook"]["status"] == "skipped_no_url"


def test_non_history_schema_rows_ignored_for_snapshots(tmp_path: Path) -> None:
    hist = tmp_path / "h.jsonl"
    out = tmp_path / "a.json"
    noise = {"schema": "other", "recommended": {"mid_vol_threshold": 99.0}}
    rec = {"mid_vol_threshold": 0.2, "high_vol_threshold": 0.4}
    lines = [
        json.dumps(noise, ensure_ascii=False),
        json.dumps(_row(rec, "2026-01-01T00:00:00Z"), ensure_ascii=False),
    ]
    hist.write_text("\n".join(lines) + "\n", encoding="utf-8")
    doc = _run(hist, out)
    assert doc["reason"] == "insufficient_history"
    assert doc["history_recommended_snapshots"] == 1
    assert doc["webhook"]["status"] == "skipped_insufficient_history"
