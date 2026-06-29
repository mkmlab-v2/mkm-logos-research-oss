"""Smoke for hybrid router v3 SSOT wire spike [HYPO]."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
BASE = ROOT / "reports/compression_hybrid_router_spike_v1_latest.json"
V3 = ROOT / "reports/compression_conditional_fusion_ablation_v3_ssot_guard_v1_latest.json"
OUT = ROOT / "reports/_test_compression_hybrid_router_v3_wire_v1.json"


def test_hybrid_v3_wire_exit_0() -> None:
    if not BASE.is_file() or not V3.is_file():
        return
    proc = subprocess.run(
        [
            PY,
            "scripts/run_compression_hybrid_router_v3_wire_spike_v1.py",
            "--out-json",
            str(OUT.relative_to(ROOT)).replace("\\", "/"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_hybrid_router_v3_wire_spike_v1"
    assert doc["send_gate"] == "HOLD"
    g40 = next(c for c in doc["corpora"] if c["corpus_id"] == "golden40_internal")
    assert g40["route"]["backend"] == "mkm_conditional_fusion_v3_ssot_guard"
    j = float((g40["result"]["raw"] or {})["mean_jaccard_proxy"])
    assert j >= 0.85
