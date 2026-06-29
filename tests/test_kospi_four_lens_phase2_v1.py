"""Phase-2 smoke: field event graph + conditional fusion ablation."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_field_event_graph_builder():
    cp = subprocess.run(
        [sys.executable, "scripts/build_field_kospi_event_graph_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads((ROOT / "reports/field_kospi_event_graph_v1_latest.json").read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "field_kospi_event_graph_v1"
    assert len(doc["nodes"]) >= 2


def test_conditional_fusion_ablation():
    subprocess.run(
        [sys.executable, "scripts/build_kospi_four_lens_graphrag_fusion_v1.py"],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        timeout=60,
    )
    cp = subprocess.run(
        [sys.executable, "scripts/run_kospi_four_lens_conditional_fusion_ablation_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(
        (ROOT / "reports/kospi_four_lens_conditional_fusion_ablation_v1_latest.json").read_text(encoding="utf-8-sig")
    )
    assert "metrics" in doc
    assert "delta_fusion_minus_active" in doc["metrics"]
