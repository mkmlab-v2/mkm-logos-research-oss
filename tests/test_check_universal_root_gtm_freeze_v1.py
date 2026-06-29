"""GTM FREEZE gate — UR-W1 maintainer bump block while external_repro=0."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts/check_universal_root_gtm_freeze_v1.py"
BUMP = ROOT / "scripts/post_universal_root_discussions_bump_v1.py"
RUN_COMPARE = ROOT / "scripts/run_universal_root_baseline_compare_v1.py"
FREEZE_SSOT = ROOT / "docs/final/artifacts/universal_root_gtm_freeze_v1_latest.json"
B0_SPEC = ROOT / "docs/final/artifacts/universal_root_baseline_b0_spec_v1.json"
GTM = ROOT / "reports/universal_root_community_gtm_v1_latest.json"
ALIAS = ROOT / "reports/baseline_vs_dual_plane_v1.json"


def test_freeze_ssot_exists_and_blocks_public_gtm():
    doc = json.loads(FREEZE_SSOT.read_text(encoding="utf-8-sig"))
    assert doc["public_gtm_allowed"] is False
    assert doc["rules"]["min_external_repro_for_gtm"] == 1
    assert doc["rules"]["gtm_unfreeze_master_key"] == "external_repro_count >= 1"
    assert "self_evolution_learnings" in doc


def test_b0_spec_has_fixture_hash_not_literal_lock():
    spec = json.loads(B0_SPEC.read_text(encoding="utf-8-sig"))
    assert spec["fixture_sha256"]
    assert spec["b0_definition"]["primary_metric"] == "english_only_hit_rate"
    assert "0.7804" not in json.dumps(spec)


def test_run_compare_creates_alias():
    proc = subprocess.run(
        [sys.executable, str(RUN_COMPARE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ALIAS.is_file()
    alias = json.loads(ALIAS.read_text(encoding="utf-8-sig"))
    assert alias.get("alias_of")


def test_check_freeze_strict_integrity_patch_gtm_exit_0():
    proc = subprocess.run(
        [sys.executable, str(CHECK), "--strict-integrity", "--patch-gtm"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    gtm = json.loads(GTM.read_text(encoding="utf-8-sig"))
    assert gtm["milestones"]["UR-W1"]["status"] == "gtm_frozen"
    assert gtm["gtm_freeze"]["active"] is True
    assert gtm["gtm_freeze"]["public_gtm_allowed"] is False


def test_check_freeze_strict_fails_when_external_repro_zero():
    proc = subprocess.run(
        [sys.executable, str(CHECK), "--strict"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    doc = json.loads(proc.stdout.strip().splitlines()[-1])
    assert doc["public_gtm_allowed"] is False
    assert doc["integrity_ok"] is True


def test_bump_live_blocked_without_override():
    proc = subprocess.run(
        [sys.executable, str(BUMP), "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0

    proc2 = subprocess.run(
        [sys.executable, str(BUMP)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc2.returncode == 3
    out = json.loads(proc2.stdout.strip().splitlines()[-1])
    assert out["error"] == "gtm_freeze_blocked"
