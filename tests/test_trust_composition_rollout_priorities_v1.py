"""Trust Composition rollout priorities builder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_trust_composition_rollout_priorities_v1.py"
OUT = ROOT / "reports/trust_composition_rollout_priorities_v1_latest.json"
PUBLIC_COPY = ROOT / "projects/no1kmedi/marketing-site/public-copy.json"
CLINICIAN_FOOTER = ROOT / "projects/no1kmedi/src/components/ClinicianPilotDisclaimerFooter.tsx"
PERSONADIARY_OPS = ROOT / "projects/no1kmedi/src/components/personadiary/PersonadiaryOpsHome.tsx"
MKMLIFE_VOCAB = ROOT / "projects/mkm/mkm-life/lib/mkmlife-consumer-vocabulary-v1.ts"


def test_build_rollout_priorities_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert OUT.is_file()


def test_rollout_top3_schema():
    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "trust_composition_rollout_priorities_v1"
    assert len(doc["top3"]) == 3
    assert doc["top3"][0]["surface_id"] == "clinic_loi_landing"
    assert doc["send_gate"] == "HOLD"


def test_hub_and_clinician_trust_signals_present():
    pub = json.loads(PUBLIC_COPY.read_text(encoding="utf-8-sig"))
    for loc in ("ko", "en"):
        wedge = (pub.get("hub_discover") or {}).get(loc, {}).get("trust_wedge", "")
        assert len(str(wedge).strip()) >= 8
    footer = CLINICIAN_FOOTER.read_text(encoding="utf-8")
    assert "artifact" in footer and "게이트" in footer


def test_phase2_trust_wedge_signals_present():
    pd = PERSONADIARY_OPS.read_text(encoding="utf-8")
    assert 'data-trust-wedge="trust_composition_v1"' in pd
    vocab = MKMLIFE_VOCAB.read_text(encoding="utf-8")
    assert "trustWedge" in vocab
