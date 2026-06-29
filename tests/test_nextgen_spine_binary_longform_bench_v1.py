"""[HYPO] Long-form MKVS binary spine bench smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_spine_binary_billable_eval_longform_v1_latest.json"
)
SCRIPT = ROOT / "scripts/run_nextgen_spine_binary_longform_bench_v1.py"
MANIFEST = ROOT / "reports/btrack_nextgen_research_only_arms_v1_latest.json"


def test_longform_binary_bench_and_registry():
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--max-cases", "50"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["arm_id"] == "ng40_spine_binary_billable_longform_v1"
    assert doc["aggregate"]["byte_exact_subset_parity"] == 1.0
    assert doc["aggregate"]["case_count"] >= 1

    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_btrack_nextgen_promotion_candidate_packet_v1.py")],
        cwd=str(ROOT),
        check=True,
        timeout=60,
    )
    reg = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ids = {a["arm_id"] for a in reg["arms"]}
    assert "ng40_spine_binary_billable_longform_v1" in ids
