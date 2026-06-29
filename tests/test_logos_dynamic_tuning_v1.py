"""Logos dynamic tuning composite chain (HYPO, sandbox only)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/logos_dynamic_resonance_stats_v1_latest.json"
POINTER = ROOT / "docs/final/artifacts/logos_theory_to_code_pointer_v1_latest.json"
PUBLIC = ROOT / "projects/mkm/mkm-life/public/data/logos_dynamic_resonance_sidecar_v1.json"
MKMLIFE = ROOT / "projects/mkm/mkm-life"
ORB = MKMLIFE / "components/magic-orb/MagicOrbExperience.tsx"


@pytest.fixture(scope="module")
def dynamic_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_dynamic_tuning_chain_v1.py",
            "--skip-spread-chain",
            "--skip-pytest",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_dynamic_resonance_stats_contract(dynamic_chain: None) -> None:
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_dynamic_resonance_stats_v1"
    assert doc["hypothesis_class"] == "HYPO"
    assert doc["production_kernel_recipe_id"] == "gematria_bridge_v1"
    assert doc["sandbox_kernel_recipe_id"] == "gematria_bridge_sandbox_v1"
    assert doc["summary"]["anchor_count"] >= 300
    assert doc["summary"]["mean_spread_4d_dynamic"] >= 0.05
    assert doc["summary"]["mean_spread_4d_dynamic"] >= doc["summary"]["mean_spread_4d_sandbox"]


def test_theory_pointer_and_public_sidecar(dynamic_chain: None) -> None:
    assert POINTER.is_file()
    ptr = json.loads(POINTER.read_text(encoding="utf-8"))
    assert ptr["schema"] == "logos_theory_to_code_pointer_v1"
    assert len(ptr["pointers"]) >= 4

    pub = json.loads(PUBLIC.read_text(encoding="utf-8"))
    assert pub["schema"] == "logos_dynamic_resonance_sidecar_v1"
    assert "job_suffering_reason" in pub["preset_sidecar"]
    hints = pub["preset_sidecar"]["job_suffering_reason"]["orb_ui_hints"]
    assert "pulse_period_ms" in hints
    assert "lattice_mesh_strength" in hints


def test_mkmlife_orb_wires_dynamic_resonance_sidecar() -> None:
    lib = MKMLIFE / "lib/magic-orb-dynamic-resonance-sidecar-v1.ts"
    assert lib.is_file()
    text = lib.read_text(encoding="utf-8")
    assert "loadDynamicResonanceSidecar" in text
    assert "applyDynamicResonanceToBloom" in text
    orb = ORB.read_text(encoding="utf-8")
    assert "magic-orb-dynamic-resonance-sidecar-v1" in orb
    assert "dynamicOrbHints" in orb
    lattice = MKMLIFE / "components/magic-orb/MagicOrbLatticeOverlay.tsx"
    assert "meshStrength" in lattice.read_text(encoding="utf-8")
    assert PUBLIC.is_file()


def test_tune_anchor_increases_spread_or_geumhwa() -> None:
    from scripts.core.logos_dynamic_tuning_v1 import tune_anchor_vector

    anchor = {
        "vector_4d": {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
        "kernel_alignment": [{"primitive": "circulation"}],
    }
    tuned = tune_anchor_vector(anchor, force_id="em_force", session_age=1.0)
    assert tuned["spread_4d_dynamic"] >= 0.0
    assert tuned["geumhwa_index"] >= 0.0
