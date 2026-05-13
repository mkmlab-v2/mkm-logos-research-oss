"""Contract tests for apply_aramaic_mvp_alert_threshold_recommendation_v1 (sweep output → recommended)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SWEEP = ROOT / "scripts" / "sweep_aramaic_mvp_alert_thresholds_v1.py"
APPLY = ROOT / "scripts" / "apply_aramaic_mvp_alert_threshold_recommendation_v1.py"


def test_apply_rejects_wrong_sweep_schema(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"schema": "wrong"}), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(APPLY), "--sweep-json", str(bad), "--output-json", str(tmp_path / "o.json")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0


def test_sweep_then_apply_roundtrip(tmp_path: Path) -> None:
    audit = tmp_path / "a.jsonl"
    audit.write_text(
        json.dumps({"run_at_utc": "2026-05-13T10:00:00Z", "conflict_ratio": 0.05}) + "\n", encoding="utf-8"
    )
    sweep_out = tmp_path / "s.json"
    apply_out = tmp_path / "r.json"
    p1 = subprocess.run(
        [sys.executable, str(SWEEP), "--audit-jsonl", str(audit), "--output-json", str(sweep_out), "--window", "5"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert p1.returncode == 0, p1.stderr
    p2 = subprocess.run(
        [sys.executable, str(APPLY), "--sweep-json", str(sweep_out), "--output-json", str(apply_out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert p2.returncode == 0, p2.stderr
    rec = json.loads(apply_out.read_text(encoding="utf-8"))
    assert rec.get("schema") == "aramaic_mvp_alert_threshold_recommended_v1"


def test_apply_from_minimal_sweep_best(tmp_path: Path) -> None:
    sweep = tmp_path / "sweep_min.json"
    sweep.write_text(
        json.dumps(
            {
                "schema": "aramaic_mvp_alert_threshold_sweep_v1",
                "best": {
                    "conflict_alert": 0.11,
                    "conflict_critical": 0.29,
                    "streak_min": 4,
                    "score_proxy": 999.0,
                    "end_severity": "ok",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = tmp_path / "rec.json"
    proc = subprocess.run(
        [sys.executable, str(APPLY), "--sweep-json", str(sweep), "--output-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("recommended", {}).get("conflict_alert") == pytest.approx(0.11)
    assert doc.get("recommended", {}).get("streak_min") == 4
