"""Contract tests for Aramaic MVP alert threshold sweep + apply."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SWEEP = ROOT / "scripts" / "sweep_aramaic_mvp_alert_thresholds_v1.py"


def test_sweep_writes_schema_and_best(tmp_path: Path) -> None:
    audit = tmp_path / "audit.jsonl"
    rows = [
        {"run_at_utc": "2026-05-13T10:00:00Z", "conflict_ratio": 0.05},
        {"run_at_utc": "2026-05-13T11:00:00Z", "conflict_ratio": 0.04},
    ]
    audit.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    out = tmp_path / "sweep.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SWEEP),
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
    assert data.get("schema") == "aramaic_mvp_alert_threshold_sweep_v1"
    assert isinstance(data.get("rows"), list)
    assert len(data["rows"]) > 0
    best = data.get("best")
    assert isinstance(best, dict)
    assert "conflict_alert" in best and "conflict_critical" in best and "streak_min" in best


def test_evaluate_audit_tail_for_thresholds_importable() -> None:
    import importlib.util

    path = ROOT / "scripts" / "alert_aramaic_mvp_trend_v1.py"
    spec = importlib.util.spec_from_file_location("_talert", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    tail = [
        {"conflict_ratio": 0.4},
        {"conflict_ratio": 0.41},
        {"conflict_ratio": 0.42},
    ]
    ev = mod.evaluate_audit_tail_for_thresholds(tail, alert_thr=0.12, critical_thr=0.28, streak_min=3)
    assert ev["severity"] == "critical"
    assert ev["streak_len"] == 3
