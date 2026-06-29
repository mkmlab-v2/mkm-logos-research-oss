"""Offline: Magic Orb consumer surface theatre condensation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MKM_LIFE = ROOT / "projects/mkm/mkm-life"


def test_consumer_theatre_condense_script_exists():
    path = MKM_LIFE / "lib/magic-orb-consumer-surface-v1.ts"
    text = path.read_text(encoding="utf-8")
    assert "condenseTheatreStepsForConsumer" in text
    assert "CONSUMER_THEATRE_GROUPS" in text or "CONSUMER_THEATRE_GROUPS" in text.replace("_GROUPS", "_GROUPS")


def test_oracle_sphere_artifact_strip_consumer_flag():
    path = MKM_LIFE / "components/magic-orb/OracleSphereArtifactStrip.tsx"
    text = path.read_text(encoding="utf-8")
    assert "consumerSurface" in text
    assert "condenseTheatreStepsForConsumer" in text
    assert "!consumerSurface" in text


def test_design_readiness_chain_still_present():
    chain = ROOT / "scripts/run_magic_orb_design_readiness_chain_v1.py"
    assert chain.is_file()


def test_builder_still_marks_consumer_ready_false_without_commander():
    builder = ROOT / "scripts/build_magic_orb_design_readiness_v1.py"
    subprocess.run(
        [sys.executable, str(builder), "--commander-visual-ok", "unset"],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    out = json.loads((ROOT / "reports/magic_orb_design_readiness_v1_latest.json").read_text(encoding="utf-8-sig"))
    assert out["consumer_ready"] is False
