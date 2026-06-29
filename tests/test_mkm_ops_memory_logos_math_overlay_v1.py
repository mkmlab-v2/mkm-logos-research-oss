"""Logos/4D/gematria ops memory overlay — Phase 1 memory pin."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "storage/meta/mkm_ops_memory_index_v1.json"


@pytest.fixture(scope="module")
def logos_math_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_mkm_ops_memory_logos_math_overlay_chain_v1.py",
            "--skip-pytest",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_logos_math_overlay_merged(logos_math_chain: None) -> None:
    index = json.loads(INDEX.read_text(encoding="utf-8-sig"))
    assert "logos_math_v1" in (index.get("overlays") or [])
    nodes = index.get("nodes") or {}
    assert "prism_ops_logos_cosmic_anchor_bridge" in nodes
    assert nodes["prism_ops_logos_cosmic_anchor_bridge"]["slice_kind"] == "json_pointer"


def test_oracle_lane_pack_auto_merges_logos_overlay(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from mkm_ops_memory_index_lib_v1 import (  # noqa: E402
        DEFAULT_INDEX_PATH,
        ensure_lane_pack_index,
        load_index,
    )

    index = load_index(ROOT / DEFAULT_INDEX_PATH.relative_to(ROOT))
    base_nodes = {
        k: v for k, v in (index.get("nodes") or {}).items() if not k.startswith("prism_ops_logos_")
    }
    stripped = {**index, "nodes": base_nodes, "overlays": []}
    merged = ensure_lane_pack_index(ROOT, stripped, "oracle")
    nodes = merged.get("nodes") or {}
    assert "prism_ops_logos_cosmic_anchor_bridge" in nodes
    assert "logos_math_v1" in (merged.get("overlays") or [])


def test_oracle_lane_pack_includes_logos_nodes(logos_math_chain: None) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from mkm_ops_memory_index_lib_v1 import LANE_OPS_PACKS  # noqa: E402

    oracle = LANE_OPS_PACKS["oracle"]
    assert "prism_ops_logos_router_regression_bundle" in oracle
    assert "prism_ops_logos_gematria_dual_gate" in oracle
    assert "prism_ops_logos_oracle_module_tier2_prep" in oracle
    assert "prism_ops_logos_narrative_closure_observability" in oracle
