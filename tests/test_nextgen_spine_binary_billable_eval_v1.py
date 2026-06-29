"""[HYPO] MKVS binary spine billable eval arm."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_spine_binary_billable_eval_v1_latest.json"
)
SCRIPT = ROOT / "scripts/run_nextgen_spine_binary_billable_eval_v1.py"


def test_spine_binary_billable_eval():
    r = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    agg = doc["aggregate"]
    assert agg["byte_exact_subset_parity"] == 1.0
    assert doc["active_auto_merge"] is False
    assert agg["global_token_saving_rate_spine_binary_billable"] == agg[
        "global_token_saving_rate"
    ]
