"""Wave 3 offline UI resonance simulation tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SIM_OUT = ROOT / "docs/final/artifacts/logos_cosmic_anchor_ui_resonance_sim_v1_latest.json"
BATCH_DIR = ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_v1"


@pytest.fixture(scope="module")
def sim_built() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_logos_cosmic_anchor_ui_resonance_sim_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_resonance_sim_schema(sim_built: None) -> None:
    sim = json.loads(SIM_OUT.read_text(encoding="utf-8"))
    manifest = json.loads(
        (ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_v1_manifest_latest.json").read_text(
            encoding="utf-8"
        )
    )
    expected = int(manifest["anchor_count"])
    assert sim["schema"] == "logos_cosmic_anchor_ui_resonance_sim_v1"
    assert sim["cf_deploy_required"] is False
    assert sim["anchor_count"] == expected
    assert len(sim["per_anchor"]) == expected


def test_scenario_runs_light_door_seed(sim_built: None) -> None:
    sim = json.loads(SIM_OUT.read_text(encoding="utf-8"))
    crisis = next(r for r in sim["scenario_runs"] if r["scenario_id"] == "motif_seed_crisis")
    assert crisis["inferred_stress"] == 0.78
    labels = {s["label"] for s in crisis["motif_samples"]}
    assert {"light", "door", "seed"}.issubset(labels)
    for sample in crisis["motif_samples"]:
        draft = sample["orb_draft"]
        assert draft["forbidden_synthesis"] is True
        assert draft["schema"] == "mkmlife_cosmic_anchor_orb_draft_v1"


def test_ui_diversity_non_trivial(sim_built: None) -> None:
    sim = json.loads(SIM_OUT.read_text(encoding="utf-8"))
    summary = sim["summary"]
    assert summary["distinct_draft_fingerprints_at_stress_0.35"] >= 2
    div = summary["ui_param_diversity_at_stress_0.35"]
    assert div["min_padding_px"]["range"] > 0
    assert div["pulse_period_ms"]["range"] > 0


def test_orb_draft_mirror_matches_ts_contract(sim_built: None) -> None:
    from scripts.core.mkmlife_cosmic_anchor_orb_draft_v1 import resolve_cosmic_anchor_orb_draft

    row = json.loads((BATCH_DIR / "seed.json").read_text(encoding="utf-8"))
    draft = resolve_cosmic_anchor_orb_draft(row, 0.35)
    required = {
        "schema",
        "anchor_id",
        "stress_proxy",
        "min_padding_px",
        "layout_density",
        "harmony_pair_kind",
    }
    assert required.issubset(draft.keys())
