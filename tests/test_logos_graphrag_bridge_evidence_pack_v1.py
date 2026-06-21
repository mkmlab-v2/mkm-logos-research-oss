"""Track L L4/L5 GraphRAG bridge evidence pack smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_logos_graphrag_bridge_evidence_pack_v1() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(
        (ROOT / "docs/final/artifacts/logos_graphrag_bridge_evidence_pack_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert doc["schema"] == "logos_graphrag_bridge_evidence_pack_v1"
    assert doc["ready_for_external_send"] is False
    assert doc["non_gating"] is True
    phase1 = ((doc.get("phase_coverage") or {}).get("phase_1_lemma_verse") or {})
    assert "edge_count_manifest" in phase1
    assert "jsonl_line_count" in phase1
    assert "edge_count_mismatch" in phase1
    phase11 = ((doc.get("phase_coverage") or {}).get("phase_11_universal_root_layer_stack") or {})
    gate_phase = phase11.get("gate_spec", {}).get("phase")
    assert gate_phase and str(gate_phase).startswith("11-")
    stress = phase11.get("shallow_stress_live_32") or {}
    assert stress.get("router_hit_rate") is not None
    assert stress.get("routing_oracle_gap") is not None


def test_run_logos_track_l_l4_l5_readiness_v1_skip_l3() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_logos_track_l_l4_l5_readiness_v1.py"),
            "--skip-l3",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(
        (ROOT / "docs/final/artifacts/logos_track_l_l4_l5_readiness_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert doc["schema"] == "logos_track_l_l4_l5_readiness_v1"
    assert doc["l4_l5_ok"] is True
    l4 = ((doc.get("checks") or {}).get("l4_lemma_layer") or {})
    assert "edge_count_manifest" in l4
    assert "edge_count_effective_jsonl" in l4
    assert l4.get("edge_count_mismatch") is False
