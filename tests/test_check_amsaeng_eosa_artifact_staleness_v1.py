from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _write_heartbeat(root: Path, age_min: float) -> None:
    ts = (datetime.now(timezone.utc) - timedelta(minutes=age_min)).isoformat()
    p = root / "reports" / "amsaeng_eosa_monitoring_heartbeat_latest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps({"schema": "amsaeng_eosa_monitoring_heartbeat_v1", "generated_at_utc": ts}, indent=2),
        encoding="utf-8",
    )


def _run_script(root: Path, extra: list[str] | None = None) -> int:
    script = Path(__file__).resolve().parent.parent / "scripts" / "check_amsaeng_eosa_artifact_staleness_v1.py"
    cmd = [sys.executable, str(script), "--workspace-root", str(root), "--heartbeat-max-age-minutes", "10"]
    if extra:
        cmd.extend(extra)
    return subprocess.call(cmd, env={**os.environ, "PYTHONUTF8": "1"})


def test_staleness_ok_fresh_heartbeat(tmp_path: Path) -> None:
    _write_heartbeat(tmp_path, age_min=1.0)
    assert _run_script(tmp_path) == 0
    out = json.loads((tmp_path / "reports" / "amsaeng_eosa_staleness_probe_latest.json").read_text(encoding="utf-8"))
    assert out["worst_exit"] == 0
    assert out["heartbeat"]["status"] == "ok"


def test_staleness_degraded_stale_heartbeat(tmp_path: Path) -> None:
    _write_heartbeat(tmp_path, age_min=60.0)
    assert _run_script(tmp_path) == 1
    out = json.loads((tmp_path / "reports" / "amsaeng_eosa_staleness_probe_latest.json").read_text(encoding="utf-8"))
    assert out["worst_exit"] == 1
    assert out["heartbeat"]["status"] == "stale"


def test_staleness_critical_missing_heartbeat(tmp_path: Path) -> None:
    assert _run_script(tmp_path) == 2
    out = json.loads((tmp_path / "reports" / "amsaeng_eosa_staleness_probe_latest.json").read_text(encoding="utf-8"))
    assert out["worst_exit"] == 2
    assert out["heartbeat"]["status"] == "missing"
