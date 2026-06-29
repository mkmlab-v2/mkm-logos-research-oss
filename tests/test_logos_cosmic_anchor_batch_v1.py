"""Tests for Top 100 Logos cosmic anchor batch pipeline."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/final/artifacts/logos_motif_registry_top100_v1.json"
BATCH_DIR = ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_v1"
BATCH_MANIFEST = ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_v1_manifest_latest.json"
RESONANCE = ROOT / "docs/final/artifacts/logos_anchor_resonance_stats_latest.json"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture(scope="module")
def chain_built() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_logos_spread_tuning_chain_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_registry_has_100_slots(chain_built: None) -> None:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert reg["schema"] == "logos_motif_registry_top100_v1"
    assert reg["slot_count"] >= 100
    assert reg["enabled_count"] >= 100
    assert len(reg["entries"]) == reg["slot_count"]


def test_batch_manifest_matches_enabled(chain_built: None) -> None:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    expected = reg["enabled_count"]
    manifest = json.loads(BATCH_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["anchor_count"] == expected
    assert manifest["kernel_recipe_id"] == "gematria_bridge_v1"
    assert manifest["thermo_alias_recipe_id"] == "gematria_thermo_alias_v1"
    assert manifest["spread_aware_ranking"] is True
    assert len(list(BATCH_DIR.glob("*.json"))) == expected


def test_anchor_rows_use_slkm_not_thermo_as_vector(chain_built: None) -> None:
    path = BATCH_DIR / "seed.json"
    row = json.loads(path.read_text(encoding="utf-8"))
    v = row["vector_4d"]
    assert set(v) == {"S", "L", "K", "M"}
    total = sum(float(v[k]) for k in ("S", "L", "K", "M"))
    assert abs(total - 1.0) < 1e-6
    assert row["mapping"]["recipe_id"] == "gematria_bridge_v1"
    assert row.get("legacy_thermo_alias")
    assert "energy_intensity_raw" in row["legacy_thermo_alias"]


def test_resonance_stats_schema(chain_built: None) -> None:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    expected = reg["enabled_count"]
    stats = json.loads(RESONANCE.read_text(encoding="utf-8"))
    assert stats["schema"] == "logos_anchor_resonance_stats_v1"
    summary = stats["summary"]
    assert summary["anchor_count"] == expected
    assert "harmony_top1_share" in summary
    assert "skew_mitigation_gate" in summary
    assert len(stats["per_anchor"]) == expected


def test_spread_aware_ranking_reduces_harmony_skew(chain_built: None) -> None:
    stats = json.loads(RESONANCE.read_text(encoding="utf-8"))
    share = float(stats["summary"]["harmony_top1_share"])
    assert share < 1.0


def test_thermo_alias_module_derived_only() -> None:
    from scripts.core.gematria_thermo_alias_v1 import compute_thermo_alias

    out = compute_thermo_alias(raw_text="φως", compressed_text="φως")
    assert out["energy_intensity_raw"] > 0
    assert 1 <= out["pulse_frequency_hz"] <= 9
