"""Smoke for compression conditional fusion ablation v2 codec rerun [HYPO]."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
ROUTING = ROOT / "reports/compression_routing_confidence_ng40_manifest_v1_latest.json"
ACTIVE_CACHE = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_conditional_fusion_active_arm_v1_latest.report.json"
)
OUT = ROOT / "reports/_test_compression_conditional_fusion_ablation_v2_codec_rerun_v1.json"


def test_v2_codec_rerun_full_or_cached() -> None:
    if not ROUTING.is_file():
        return
    cmd = [
        PY,
        "scripts/run_compression_conditional_fusion_ablation_v2_codec_rerun_v1.py",
        "--output",
        str(OUT.relative_to(ROOT)).replace("\\", "/"),
        "--holdout-frac",
        "0.2",
    ]
    if ACTIVE_CACHE.is_file():
        cmd.append("--skip-codec-rerun")
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False, timeout=600)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_conditional_fusion_ablation_v2_codec_rerun_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["protocol"]["proxy_only"] is False
    assert doc["golden40_codec_arms"]["conditional_merged"]["case_count"] == 40
    assert "knee_j_guard" in doc["policy_counts"]
