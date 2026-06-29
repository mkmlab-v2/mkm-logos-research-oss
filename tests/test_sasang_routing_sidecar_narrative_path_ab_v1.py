"""B-track: sasang routing sidecar × narrative path A/B bench."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.core.sasang_routing_sidecar_narrative_ab_v1 import (  # noqa: E402
    apply_entropy_profile,
    apply_sidecar_narrowing,
    resolve_sample_ids,
    sidecar_narrowing_caps,
)

SIDECAR = ROOT / "docs/final/artifacts/sasang_routing_sidecar_on_gematria_path_v1_latest.json"
AB = ROOT / "reports/sasang_routing_sidecar_narrative_path_ab_v1_latest.json"
CHAIN = ROOT / "reports/sasang_routing_sidecar_narrative_path_ab_chain_v1_latest.json"


def test_sidecar_narrowing_reduces_router_cap() -> None:
    sidecar = json.loads(SIDECAR.read_text(encoding="utf-8"))
    caps = sidecar_narrowing_caps(sidecar)
    assert caps["max_router_paths"] <= 6
    row = {
        "sample_id": "smoke",
        "sample_pass": True,
        "router_paths": 6,
        "hop_count": 3,
        "flow_score": 1.0,
    }
    out = apply_sidecar_narrowing(row, sidecar)
    assert out["narrowed_router_paths"] <= row["router_paths"]
    assert out["router_paths_delta"] <= 0


def test_entropy_profile_tactical_is_stricter_than_observe() -> None:
    sidecar = json.loads(SIDECAR.read_text(encoding="utf-8"))
    observe = sidecar_narrowing_caps(apply_entropy_profile(sidecar, "observe"))
    tactical = sidecar_narrowing_caps(apply_entropy_profile(sidecar, "tactical"))
    assert tactical["max_router_paths"] <= observe["max_router_paths"]
    assert tactical["max_hop_count"] <= observe["max_hop_count"]


def test_resolve_sample_ids_full_panel() -> None:
    bridge = json.loads(
        (ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    panel = {"panel_mode": "full"}
    ids = resolve_sample_ids(panel, bridge)
    assert len(ids) == 200


def test_ab_chain_skip_router_exit0() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            "scripts/run_sasang_routing_sidecar_narrative_path_ab_chain_v1.py",
            "--skip-router",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    assert AB.is_file()
    doc = json.loads(AB.read_text(encoding="utf-8"))
    assert doc["schema"] == "sasang_routing_sidecar_narrative_path_ab_v1"
    assert doc["forbidden_synthesis_ack"] is True
    assert doc["panel_sample_count"] == 8
    assert CHAIN.is_file()


@pytest.mark.skipif(not AB.is_file(), reason="run ab chain first")
def test_ab_gate_pass_rate_floor() -> None:
    doc = json.loads(AB.read_text(encoding="utf-8"))
    assert doc["arm_on"]["sidecar_gate_pass_rate"] >= 0.875
    assert doc["delta"]["narrowed_router_paths_minus_baseline"] <= 0
