"""Probe tiers + preset builder smoke (offline)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "scripts/probe_mkmlife_magic_orb_live_v1.py"
JOB_PROBE = ROOT / "scripts/probe_mkmlife_magic_orb_job_four_slot_live_v1.py"
BUILDER = ROOT / "scripts/build_magic_orb_query_presets_from_fixture_v1.py"
MANIFEST = ROOT / "docs/final/fixtures/magic_orb_query_presets_manifest_v1.json"


def test_probe_script_tiers_and_profiles():
    text = PROBE.read_text(encoding="utf-8")
    assert "magic_orb_live_probe_v1" in text
    assert '"tier": "core"' in text
    assert '"tier": "job_four_slot"' in text
    assert "--profile" in text
    assert "forbid_markers" in text
    assert "mkmlife_hero_slices_static" in text
    assert "integrity_tier" in text
    assert "마법구슬" in text  # forbidden, not required marker


def test_job_probe_wrapper_exists():
    text = JOB_PROBE.read_text(encoding="utf-8")
    assert "job_four_slot" in text
    assert "probe_mkmlife_magic_orb_live_v1.py" in text


def test_build_presets_from_manifest():
    proc = subprocess.run(
        [sys.executable, str(BUILDER), "--skip-sync-public"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    summary = json.loads(proc.stdout.strip().splitlines()[-1])
    assert summary["ok"] is True
    assert "job_suffering_reason" in summary["preset_ids"]
    ts = (ROOT / "projects/mkm/mkm-life/lib/magic-orb-query-presets-v1.ts").read_text(encoding="utf-8")
    assert "PRESET_IMMERSIVE_QUERY_IDS" in ts
    assert "dc73c2c367199e48" in ts
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["schema"] == "magic_orb_query_presets_manifest_v1"
