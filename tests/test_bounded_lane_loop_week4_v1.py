"""Bounded lane loop Week 4 — meta envelope hook + A2A briefing sample."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_bounded_lane_loop_v1.py"
FIXTURE = ROOT / "docs/final/artifacts/fixtures/bounded_lane_pin_infra_v1.example.json"
META_FIXTURE = (
    ROOT / "docs/final/artifacts/fixtures/mkm_meta_layer_turn_envelope_v1.example.json"
)
A2A_BUILDER = ROOT / "scripts/build_bounded_lane_a2a_briefing_sample_v1.py"
A2A_FIXTURE = ROOT / "docs/final/artifacts/fixtures/bounded_lane_a2a_briefing_sample_v1.json"
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


def test_dry_run_with_meta_envelope_includes_summary_block() -> None:
    proc = _run(
        [
            "--pin",
            str(FIXTURE),
            "--dry-run",
            "--meta-layer-envelope-path",
            str(META_FIXTURE),
        ]
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    meta = doc.get("meta_layer_envelope") or {}
    assert meta.get("ok") is True
    assert meta.get("risk_tier") == "LOW"
    assert doc["outcome_class"] == "shadow_pass"


def test_dry_run_invalid_meta_envelope_shadow_warning() -> None:
    bad = ROOT / "reports/_meta_envelope_bad_bounded_lane_v1.json"
    bad.write_text('{"schema":"mkm_meta_layer_turn_envelope_v1"}', encoding="utf-8")
    try:
        proc = _run(
            [
                "--pin",
                str(FIXTURE),
                "--dry-run",
                "--meta-layer-envelope-path",
                str(bad),
            ]
        )
        assert proc.returncode == 0, proc.stderr
        doc = json.loads(OUT.read_text(encoding="utf-8"))
        assert doc["meta_layer_envelope"]["ok"] is False
        assert doc["outcome_class"] == "shadow_warning"
    finally:
        bad.unlink(missing_ok=True)


def test_build_a2a_briefing_sample_fixture() -> None:
    proc = subprocess.run(
        [sys.executable, str(A2A_BUILDER), "--lane", "infra"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(A2A_FIXTURE.read_text(encoding="utf-8"))
    assert doc["schema"] == "bounded_lane_a2a_briefing_sample_v1"
    assert doc["lane"] == "infra"
    assert doc["hypothesis_tier"] == "B"
    assert doc.get("briefing_one_line")
    assert doc["dialogue_mock_summary"]["turns_recorded"] == 2
