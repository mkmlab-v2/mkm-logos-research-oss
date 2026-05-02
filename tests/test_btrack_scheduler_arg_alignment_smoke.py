from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_control_tower_autopush_forwards_min_accuracy() -> None:
    script = (ROOT / "scripts" / "Run-BtrackControlTowerOps.ps1").read_text(encoding="utf-8")
    assert "AutopushMinAccuracyDelta" in script
    assert "-MinAccuracyDelta" in script


def test_control_tower_task_register_includes_autopush_min_accuracy() -> None:
    script = (ROOT / "scripts" / "Register-BtrackControlTowerOpsTasks.ps1").read_text(encoding="utf-8")
    assert "AutopushMinAccuracyDelta" in script
    assert "-AutopushMinAccuracyDelta" in script


def test_health_snapshot_has_summary_flags() -> None:
    script = (ROOT / "scripts" / "build_btrack_automation_health_snapshot_v1.py").read_text(encoding="utf-8")
    assert '"all_tasks_ok"' in script
    assert '"all_artifacts_ok"' in script
    assert '"ops_ready"' in script
