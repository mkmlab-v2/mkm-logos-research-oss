"""Trust Composition glass/blur commander visual A/B chain."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "scripts/run_trust_composition_glass_blur_commander_visual_chain_v1.py"
READINESS = ROOT / "reports/trust_composition_glass_blur_readiness_v1_latest.json"
COMMANDER = ROOT / "reports/trust_composition_glass_blur_commander_visual_v1_latest.json"
FIGMA_PACK = ROOT / "reports/clinic_loi_figma_reverse_sync_pack_v1_latest.json"
PLAYWRIGHT = ROOT / "scripts/capture_trust_composition_glass_blur_ab_playwright_v1.mjs"


def test_playwright_ab_script_present():
    text = PLAYWRIGHT.read_text(encoding="utf-8")
    assert "panel--flat" in text
    assert "panel--glass" in text
    assert "trust_composition_glass_blur_screenshot_ab_v1.png" in text


def test_commander_visual_chain_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(CHAIN), "--skip-pytest"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    readiness = json.loads(READINESS.read_text(encoding="utf-8-sig"))
    assert readiness["experiment_ready"] is True
    assert readiness["ab_verdict"] == "prefer_flat_baseline"
    assert readiness["not_clinic_loi_default"] is True
    commander = json.loads(COMMANDER.read_text(encoding="utf-8-sig"))
    assert commander["clinic_loi_default"] == "flat"
    assert FIGMA_PACK.is_file()
