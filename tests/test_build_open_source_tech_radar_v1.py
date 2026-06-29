"""build_open_source_tech_radar_v1 + guardrail autopilot scaffold contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_guardrail_upgrade_autopilot_v1 import build_autopilot  # noqa: E402
from build_open_source_tech_radar_v1 import build_radar  # noqa: E402


def test_build_radar_offline_schema() -> None:
    doc = build_radar(include_fetch=False, previous=None)
    assert doc["schema_version"] == "open_source_tech_radar_v1"
    assert doc["disclaimer"] == "research_only"
    assert doc["build_mode"] == "offline_refresh"
    assert "upgrade_targets" in doc
    assert any("Docling" in t["name"] for t in doc["upgrade_targets"])


def test_build_autopilot_schema() -> None:
    radar = build_radar(include_fetch=False, previous=None)
    doc = build_autopilot(radar=radar, safe_ops=None, trading_health=None)
    assert doc["schema_version"] == "guardrail_upgrade_autopilot_v1"
    assert doc["disclaimer"] == "research_only"
    assert doc["execution_queue"]


def test_main_writes_radar_json(tmp_path: Path) -> None:
    out = tmp_path / "radar.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_open_source_tech_radar_v1.py"),
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == "open_source_tech_radar_v1"
