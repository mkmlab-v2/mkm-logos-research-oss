"""Phase 1: magic_orb_hero_slices_v1 bundle (passion + Dan.2 + chronology)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_magic_orb_hero_slices_bundle_v1.py"
ARTIFACT = ROOT / "docs/final/artifacts/magic_orb_hero_slices_v1_latest.json"
MKMLIFE = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_hero_slices_v1.json"


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_magic_orb_hero_slices_bundle_v1", BUILDER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_build_bundle_schema_and_caps():
    mod = _load_builder()
    bundle = mod.build_bundle()
    assert bundle["schema"] == "magic_orb_hero_slices_v1"
    assert bundle["research_only"] is True
    assert bundle["non_gating"] is True
    assert len(bundle["slices"]) == 2
    assert bundle["default_slice_id"] == "SYNOPTIC_PASSION_WEEK_v1"
    assert len(bundle["chronology"]["eras"]) >= 5

    by_id = {s["slice_id"]: s for s in bundle["slices"]}
    passion = by_id["SYNOPTIC_PASSION_WEEK_v1"]["graph_bloom"]
    dan2 = by_id["DAN2_CLUSTER_v1"]["graph_bloom"]

    assert passion["schema"] == "magic_orb_graph_bloom_v1"
    assert passion["stats"]["node_count"] <= 64
    assert passion["stats"]["edge_count"] <= 72

    assert dan2["schema"] == "magic_orb_graph_bloom_v1"
    assert dan2["stats"]["node_count"] <= 64
    assert dan2["stats"]["edge_count"] <= 72
    assert dan2["stats"]["node_count"] >= 20

    gospel = next(e for e in bundle["chronology"]["eras"] if e["era_id"] == "gospel_logos_incarnate")
    exile = next(e for e in bundle["chronology"]["eras"] if e["era_id"] == "exile_and_return")
    assert gospel["hint_slice_id"] == "SYNOPTIC_PASSION_WEEK_v1"
    assert exile["hint_slice_id"] == "DAN2_CLUSTER_v1"


def test_cli_writes_artifact(tmp_path):
    out = tmp_path / "bundle.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--out",
            str(out),
            "--sync-mkmlife",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "magic_orb_hero_slices_v1"


def test_promoted_artifact_exists_after_build():
    if not ARTIFACT.is_file():
        subprocess.run(
            [sys.executable, str(BUILDER), "--sync-mkmlife"],
            cwd=str(ROOT),
            check=True,
        )
    assert ARTIFACT.is_file()
    doc = json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "magic_orb_hero_slices_v1"
