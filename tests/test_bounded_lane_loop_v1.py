"""Bounded lane loop v1 — pin schema, whitelist gate, shadow outcomes."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_bounded_lane_loop_v1.py"
FIXTURE = ROOT / "docs/final/artifacts/fixtures/bounded_lane_pin_infra_v1.example.json"
WHITELIST = ROOT / "docs/final/artifacts/bounded_lane_loop_whitelist_v1.json"
OUT = ROOT / "reports/bounded_lane_loop_v1_latest.json"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNNER), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_dry_run_fixture_exit_ok() -> None:
    proc = _run(["--pin", str(FIXTURE), "--dry-run"])
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "bounded_lane_loop_v1"
    assert doc["outcome_class"] in {"shadow_pass", "shadow_warning", "shadow_reject"}
    assert doc["shadow_only"] is True if "shadow_only" in doc else doc.get("todo_queue_auto_enqueue") is False
    assert doc["todo_queue_auto_enqueue"] is False
    assert doc["track_a_promote"] is False


def test_whitelist_blocks_forbidden_substring() -> None:
    bad_pin = ROOT / "reports/_bounded_lane_pin_test_bad_v1.json"
    pin = json.loads(FIXTURE.read_text(encoding="utf-8"))
    pin["steps"] = [
        {
            "step_id": "evil",
            "runner": "python",
            "argv": ["scripts/push-internal.ps1"],
        }
    ]
    bad_pin.write_text(json.dumps(pin), encoding="utf-8")
    try:
        proc = _run(["--pin", str(bad_pin), "--dry-run"])
        assert proc.returncode == 2
        doc = json.loads(OUT.read_text(encoding="utf-8"))
        assert doc["outcome_class"] == "shadow_reject"
        assert doc["policy_violations"]
    finally:
        bad_pin.unlink(missing_ok=True)


def test_whitelist_json_has_required_fields() -> None:
    wl = json.loads(WHITELIST.read_text(encoding="utf-8"))
    assert wl["schema"] == "bounded_lane_loop_whitelist_v1"
    assert wl["allowed_invocations"]
    assert wl["forbidden_argv_substrings"]
