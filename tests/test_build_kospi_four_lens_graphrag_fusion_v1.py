"""Smoke: KOSPI 4-lens GraphRAG fusion pack builder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_kospi_four_lens_graphrag_fusion_v1_exit_zero():
    cp = subprocess.run(
        [sys.executable, "scripts/build_kospi_four_lens_graphrag_fusion_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr[-500:]
    out = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "kospi_four_lens_graphrag_fusion_v1"
    assert doc["send_gate"] == "HOLD"
    assert "field" in doc
    assert set(doc["lenses"]) == {"logos", "myeongni", "sasang"}
    assert doc["fusion_resolution"]["final_action"] in ("WATCH", "HOLD", "REDUCE")
