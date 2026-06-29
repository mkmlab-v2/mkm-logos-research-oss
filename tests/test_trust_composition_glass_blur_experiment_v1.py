"""Trust Composition glass/blur experiment gate."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts/check_trust_composition_glass_blur_experiment_v1.py"
OUT = ROOT / "reports/trust_composition_glass_blur_gate_v1_latest.json"
PREVIEW = ROOT / "reports/trust_composition_glass_blur_preview_v1.html"


def test_glass_blur_gate_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(GATE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    assert doc["decision"] == "PASS"
    assert doc["not_clinic_loi_default"] is True


def test_preview_experiment_markers():
    text = PREVIEW.read_text(encoding="utf-8")
    assert 'data-experiment="glass_blur_v1"' in text
    assert "근거 없으면" in text
    assert "clinic LOI 기본 적용 금지" in text
