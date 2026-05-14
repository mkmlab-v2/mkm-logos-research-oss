"""CLI + JSON Schema for insight survivor health alert (Track T)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "alert_insight_survivor_health_v1.py"

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]


def _run(args: list[str]) -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout


def _survivor_doc(scores: list[float]) -> dict:
    surv = [{"fusion_candidate_score": s} for s in scores]
    return {
        "schema": "insight_survivor_candidates_v1",
        "survivor_count": len(surv),
        "survivors": surv,
    }


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_insight_survivor_health_no_history_path_schema(tmp_path: Path) -> None:
    schema = json.loads(
        (ROOT / "docs/final/schemas/insight_survivor_health_alert_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    surv = tmp_path / "surv.json"
    out = tmp_path / "alert.json"
    surv.write_text(json.dumps(_survivor_doc([0.7, 0.5]), ensure_ascii=False), encoding="utf-8")
    _run(["--survivor-json", str(surv), "--output-json", str(out)])
    doc = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
    assert doc.get("reason") == "insufficient_history"
    assert doc.get("should_alert") is False
    assert doc["webhook"]["status"] == "skipped_no_history_jsonl"


def test_insight_survivor_health_history_stable(tmp_path: Path) -> None:
    hist = tmp_path / "h.jsonl"
    row = {
        "schema": "insight_survivor_health_history_row_v1",
        "generated_at_utc": "2026-01-01T00:00:00Z",
        "latest": {"survivor_count": 2, "survivor_mean_score": 0.6},
    }
    hist.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    surv = tmp_path / "surv.json"
    out = tmp_path / "alert.json"
    surv.write_text(json.dumps(_survivor_doc([0.6, 0.6]), ensure_ascii=False), encoding="utf-8")
    _run(
        [
            "--survivor-json",
            str(surv),
            "--output-json",
            str(out),
            "--history-jsonl",
            str(hist),
            "--drift-threshold-mean",
            "0.2",
            "--drift-threshold-count",
            "5",
        ]
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["reason"] == "stable_below_threshold"
    assert doc["should_alert"] is False
    assert doc["deltas"]["survivor_mean_score"] == 0.0
    assert doc["webhook"]["status"] == "skipped_should_false"


def test_insight_survivor_health_history_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INSIGHT_SURVIVOR_HEALTH_ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("OPS_ALARM_WEBHOOK_URL", raising=False)
    hist = tmp_path / "h.jsonl"
    row = {
        "schema": "insight_survivor_health_history_row_v1",
        "generated_at_utc": "2026-01-01T00:00:00Z",
        "latest": {"survivor_count": 1, "survivor_mean_score": 0.2},
    }
    hist.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    surv = tmp_path / "surv.json"
    out = tmp_path / "alert.json"
    surv.write_text(json.dumps(_survivor_doc([0.9]), ensure_ascii=False), encoding="utf-8")
    _run(
        [
            "--survivor-json",
            str(surv),
            "--output-json",
            str(out),
            "--history-jsonl",
            str(hist),
            "--drift-threshold-mean",
            "0.05",
            "--drift-threshold-count",
            "1",
        ]
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["reason"] == "health_drift"
    assert doc["should_alert"] is True
    assert doc["deltas"]["survivor_mean_score"] == pytest.approx(0.7)
    assert doc["webhook"]["status"] == "skipped_no_url"


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_insight_survivor_health_append_history_row_schema(tmp_path: Path) -> None:
    row_schema = json.loads(
        (ROOT / "docs/final/schemas/insight_survivor_health_history_row_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    hist = tmp_path / "h.jsonl"
    surv = tmp_path / "surv.json"
    out = tmp_path / "alert.json"
    surv.write_text(json.dumps(_survivor_doc([0.4]), ensure_ascii=False), encoding="utf-8")
    _run(
        [
            "--survivor-json",
            str(surv),
            "--output-json",
            str(out),
            "--history-jsonl",
            str(hist),
            "--append-history",
        ]
    )
    lines = [ln for ln in hist.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    row = json.loads(lines[0])
    jsonschema.validate(instance=row, schema=row_schema)
    alert_doc = json.loads(out.read_text(encoding="utf-8"))
    alert_schema = json.loads(
        (ROOT / "docs/final/schemas/insight_survivor_health_alert_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.validate(instance=alert_doc, schema=alert_schema)
    assert alert_doc["webhook"]["status"] == "skipped_insufficient_history"


def test_insight_survivor_health_empty_history_file_webhook(tmp_path: Path) -> None:
    hist = tmp_path / "empty.jsonl"
    hist.write_text("", encoding="utf-8")
    surv = tmp_path / "surv.json"
    out = tmp_path / "alert.json"
    surv.write_text(json.dumps(_survivor_doc([0.5]), ensure_ascii=False), encoding="utf-8")
    _run(
        [
            "--survivor-json",
            str(surv),
            "--output-json",
            str(out),
            "--history-jsonl",
            str(hist),
        ]
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["reason"] == "insufficient_history"
    assert doc["webhook"]["status"] == "skipped_insufficient_history"


def test_insight_survivor_health_drift_dry_run_webhook(tmp_path: Path) -> None:
    hist = tmp_path / "h.jsonl"
    row = {
        "schema": "insight_survivor_health_history_row_v1",
        "generated_at_utc": "2026-01-01T00:00:00Z",
        "latest": {"survivor_count": 1, "survivor_mean_score": 0.1},
    }
    hist.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    surv = tmp_path / "surv.json"
    out = tmp_path / "alert.json"
    surv.write_text(json.dumps(_survivor_doc([0.9]), ensure_ascii=False), encoding="utf-8")
    _run(
        [
            "--survivor-json",
            str(surv),
            "--output-json",
            str(out),
            "--history-jsonl",
            str(hist),
            "--drift-threshold-mean",
            "0.05",
            "--dry-run",
        ]
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["reason"] == "health_drift"
    assert doc["webhook"]["status"] == "skipped_dry_run"
