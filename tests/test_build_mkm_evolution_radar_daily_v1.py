"""build_mkm_evolution_radar_daily_v1 contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_mkm_evolution_radar_daily_v1 import build_radar  # noqa: E402


def test_build_radar_schema() -> None:
    doc = build_radar(include_fetch=False)
    assert doc["schema"] == "mkm_evolution_radar_daily_v1"
    assert doc["human_approval_required"] is True
    assert doc["auto_apply"] == "none"
    assert doc["research_only"] is True


def test_main_writes_json(tmp_path: Path) -> None:
    out = tmp_path / "radar.json"
    import subprocess

    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_mkm_evolution_radar_daily_v1.py"),
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema"] == "mkm_evolution_radar_daily_v1"
