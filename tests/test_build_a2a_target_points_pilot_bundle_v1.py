"""A2A target points pilot bundle smoke."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from scripts.build_a2a_target_points_pilot_bundle_v1 import PILOT_STEPS, run_bundle

ROOT = Path(__file__).resolve().parents[1]


def test_pilot_steps_scripts_exist():
    for spec in PILOT_STEPS:
        assert (ROOT / spec["script"]).is_file()


def test_run_bundle_dry_with_mocked_subprocess(tmp_path):
    def fake_run(cmd, cwd=None, capture_output=True, text=True):  # noqa: ANN001
        class R:
            returncode = 0
            stdout = "WROTE: ok\n"
            stderr = ""

        return R()

    with patch("scripts.build_a2a_target_points_pilot_bundle_v1.subprocess.run", fake_run):
        with patch(
            "scripts.build_a2a_target_points_pilot_bundle_v1.TARGET_POINTS",
            ROOT / "docs/final/artifacts/a2a_target_points_v1_latest.json",
        ):
            doc = run_bundle(include_pytest=False, strict_exit=False)
    assert doc["schema"] == "a2a_target_points_pilot_bundle_v1"
    assert len(doc["steps"]) >= 4
    assert doc["steps"][0]["id"] == "tp01"


def test_emit_script_writes_json(tmp_path, monkeypatch):
    out = tmp_path / "bundle.json"

    def fake_run(cmd, cwd=None, capture_output=True, text=True):  # noqa: ANN001
        class R:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return R()

    monkeypatch.setattr(
        "sys.argv",
        ["build_a2a_target_points_pilot_bundle_v1.py", "--out", str(out)],
    )
    monkeypatch.setattr(
        "scripts.build_a2a_target_points_pilot_bundle_v1.subprocess.run",
        fake_run,
    )
    from scripts.build_a2a_target_points_pilot_bundle_v1 import main

    assert main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload.get("schema") == "a2a_target_points_pilot_bundle_v1"
