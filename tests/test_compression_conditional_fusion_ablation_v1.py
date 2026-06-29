"""Smoke for compression conditional fusion ablation [HYPO]."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
ROUTING = ROOT / "reports/compression_routing_confidence_ng40_manifest_v1_latest.json"
OUT = ROOT / "reports/_test_compression_conditional_fusion_ablation_v1.json"


def test_conditional_fusion_ablation_exit_0() -> None:
    if not ROUTING.is_file():
        return
    proc = subprocess.run(
        [
            PY,
            "scripts/run_compression_conditional_fusion_ablation_v1.py",
            "--output",
            str(OUT.relative_to(ROOT)).replace("\\", "/"),
            "--holdout-frac",
            "0.2",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_conditional_fusion_ablation_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["apply_forbidden"] is True
    assert doc["protocol"]["proxy_only"] is True
    assert "baseline_active" in doc["golden40_arms_full"]
    assert "conditional_fusion_v1" in doc["golden40_compare_holdout"]
    assert doc["golden40_arms_full"]["baseline_active"]["case_count"] == 40
    assert len(doc["protocol"]["holdout_case_ids"]) >= 1
