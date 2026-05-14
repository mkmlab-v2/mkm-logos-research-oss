"""JSON Schema: aramaic_insight_cap_threshold_drift_alert_v1 (drift alert artifact)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "alert_aramaic_insight_cap_threshold_drift_v1.py"
HISTORY_ROW_SCHEMA = "aramaic_insight_cap_bucket_threshold_history_row_v1"

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]


def _hist_row(rec: dict[str, float | int], ts: str) -> dict:
    return {"schema": HISTORY_ROW_SCHEMA, "recorded_at_utc": ts, "recommended": rec}


def _full_rec() -> dict[str, float]:
    return {
        "mid_vol_threshold": 0.2,
        "high_vol_threshold": 0.4,
        "insight_max_delta_low_vol": 0.06,
        "insight_max_delta_mid_vol": 0.045,
        "insight_max_delta_high_vol": 0.03,
    }


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_drift_alert_example_json_validates() -> None:
    schema = json.loads(
        (
            ROOT / "docs/final/schemas/aramaic_insight_cap_threshold_drift_alert_v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    example = json.loads(
        (
            ROOT / "docs/final/schemas/aramaic_insight_cap_threshold_drift_alert_v1.example.json"
        ).read_text(encoding="utf-8")
    )
    jsonschema.validate(instance=example, schema=schema)


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_drift_alert_insufficient_history_instance_validates() -> None:
    schema = json.loads(
        (
            ROOT / "docs/final/schemas/aramaic_insight_cap_threshold_drift_alert_v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    instance = {
        "schema": "aramaic_insight_cap_threshold_drift_alert_v1",
        "generated_at_utc": "2026-05-13T12:00:00Z",
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "history_rows": 0,
        "history_recommended_snapshots": 0,
        "drift_threshold": 0.0001,
        "should_alert": False,
        "reason": "insufficient_history",
        "max_abs_delta": 0.0,
        "drifted_keys": [],
        "deltas": {},
        "webhook": {"sent": False, "status": "skipped_insufficient_history"},
    }
    jsonschema.validate(instance=instance, schema=schema)


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_cli_stable_output_validates_against_schema(tmp_path: Path) -> None:
    schema = json.loads(
        (
            ROOT / "docs/final/schemas/aramaic_insight_cap_threshold_drift_alert_v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    hist = tmp_path / "h.jsonl"
    out = tmp_path / "out.json"
    r = _full_rec()
    lines = [
        json.dumps(_hist_row(r, "2026-01-01T00:00:00Z"), ensure_ascii=False),
        json.dumps(_hist_row(r, "2026-01-02T00:00:00Z"), ensure_ascii=False),
    ]
    hist.write_text("\n".join(lines) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--history-jsonl",
            str(hist),
            "--output-json",
            str(out),
            "--drift-threshold",
            "1e-4",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["reason"] == "stable_below_threshold"
    jsonschema.validate(instance=doc, schema=schema)


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_cli_threshold_drift_dry_run_output_validates_against_schema(tmp_path: Path) -> None:
    schema = json.loads(
        (
            ROOT / "docs/final/schemas/aramaic_insight_cap_threshold_drift_alert_v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    hist = tmp_path / "h.jsonl"
    out = tmp_path / "out.json"
    r1 = _full_rec()
    r2 = dict(r1)
    r2["mid_vol_threshold"] = 0.35
    lines = [
        json.dumps(_hist_row(r1, "2026-01-01T00:00:00Z"), ensure_ascii=False),
        json.dumps(_hist_row(r2, "2026-01-02T00:00:00Z"), ensure_ascii=False),
    ]
    hist.write_text("\n".join(lines) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--history-jsonl",
            str(hist),
            "--output-json",
            str(out),
            "--drift-threshold",
            "0.01",
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["reason"] == "threshold_drift"
    assert doc["should_alert"] is True
    jsonschema.validate(instance=doc, schema=schema)
