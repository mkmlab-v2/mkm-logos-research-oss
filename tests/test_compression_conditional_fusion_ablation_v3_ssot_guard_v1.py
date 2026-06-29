"""Smoke for compression conditional fusion ablation v3 SSOT guard [HYPO]."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
ROUTING = ROOT / "reports/compression_routing_confidence_ng40_manifest_v1_latest.json"
V2_CODEC = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_conditional_fusion_active_arm_v1_latest.report.json"
)
OUT = ROOT / "reports/_test_compression_conditional_fusion_ablation_v3_ssot_guard_v1.json"


def test_v3_ssot_guard_exit_0() -> None:
    if not ROUTING.is_file() or not V2_CODEC.is_file():
        return
    proc = subprocess.run(
        [
            PY,
            "scripts/run_compression_conditional_fusion_ablation_v3_ssot_guard_codec_rerun_v1.py",
            "--output",
            str(OUT.relative_to(ROOT)).replace("\\", "/"),
            "--holdout-frac",
            "0.2",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_conditional_fusion_ablation_v3_ssot_guard_v1"
    assert doc["recommended_policy"] is True
    assert doc["send_gate"] == "HOLD"
    knee_n = doc["policy_counts"].get("knee_j_guard", 0)
    assert knee_n >= 1
    assert knee_n <= 8
    v2c = doc.get("v2_compare") or {}
    assert "v3_minus_v2_saving_pp" in v2c
