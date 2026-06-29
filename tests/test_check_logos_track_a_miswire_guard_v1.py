"""Logos → Track A miswire static guard."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts/check_logos_track_a_miswire_guard_v1.py"
RISK_GOOD = ROOT / "projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json"
FIXTURE_BAD = ROOT / "tests/fixtures/logos_track_a_miswire_risk_profile_bad_v1.json"
CHOKEPOINT = ROOT / "projects/bitcoin-trading/scripts/run_conditional_action_gate_v1.py"


def _run(*extra: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(GUARD), *extra]
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)


def test_guard_passes_on_workspace_defaults() -> None:
    proc = _run("--json")
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads(proc.stdout)
    assert report["ok"] is True
    assert report["status"] == "PASS"
    assert report["tier_a_chokepoint_count"] >= 7


def test_risk_profile_active_mode_with_logos_score_fails() -> None:
    assert FIXTURE_BAD.is_file()
    proc = _run("--risk-profile", str(FIXTURE_BAD), "--json")
    assert proc.returncode == 1, proc.stdout
    report = json.loads(proc.stdout)
    assert report["ok"] is False
    assert any("logos_non_gating_ack" in e for e in report["errors"])


def test_tier_a_chokepoint_has_no_logos_threshold_gate() -> None:
    text = CHOKEPOINT.read_text(encoding="utf-8")
    assert "logos_regime_score" not in text
    assert "logos_concept_bridge" not in text
    assert "narrative_template" not in text
