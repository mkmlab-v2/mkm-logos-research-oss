"""Smoke: probe_mkmlife_magic_orb_live_v1 structure (offline mocks via subprocess with --help N/A)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "scripts" / "probe_mkmlife_magic_orb_live_v1.py"


def test_probe_script_exists_and_checks_defined():
    text = PROBE.read_text(encoding="utf-8")
    assert "three_lens_sphere_envelope_v1" in text
    assert "mkmlife.com/oracle-sphere" in text
    assert "magic_orb_live_probe_v1" in text
