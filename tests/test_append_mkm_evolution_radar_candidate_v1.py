"""append_mkm_evolution_radar_candidate_v1 contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from append_mkm_evolution_radar_candidate_v1 import (  # noqa: E402
    append_candidate,
    load_radar,
    validate_candidate,
)
from build_mkm_evolution_radar_daily_v1 import build_radar  # noqa: E402


def test_validate_candidate_requires_pending() -> None:
    err = validate_candidate(
        {
            "id": "x",
            "title": "t",
            "source": "s",
            "kind": "manual_followup",
            "approval_status": "approved",
            "suggested_action": "none",
        }
    )
    assert any("pending" in e for e in err)


def test_append_and_preserve_on_rebuild(tmp_path: Path) -> None:
    radar_path = tmp_path / "radar.json"
    fixture = (
        ROOT
        / "docs/final/artifacts/fixtures/mkm_evolution_radar_candidate_exa_mcp_v1.example.json"
    )
    candidate = json.loads(fixture.read_text(encoding="utf-8"))
    radar = load_radar(radar_path)
    radar, action = append_candidate(radar, candidate)
    assert action == "appended"
    radar_path.write_text(json.dumps(radar, ensure_ascii=False, indent=2), encoding="utf-8")

    rebuilt = build_radar(include_fetch=False, existing=json.loads(radar_path.read_text()))
    ids = [c["id"] for c in rebuilt["candidates"]]
    assert "exa_mcp_permissions_review" in ids


def test_main_cli(tmp_path: Path) -> None:
    import subprocess

    out = tmp_path / "radar.json"
    fixture = (
        ROOT
        / "docs/final/artifacts/fixtures/mkm_evolution_radar_candidate_myeongri_cal30_v1.example.json"
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/append_mkm_evolution_radar_candidate_v1.py"),
            "--radar-json",
            str(out),
            "--from-json",
            str(fixture),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["candidates"][0]["id"] == "myeongri_interpret_v4_calibration30_review"
