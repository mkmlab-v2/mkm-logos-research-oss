from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_build_lora_tranche2_signoff_pack_v1_runs() -> None:
    out = ROOT / "reports" / "tmp_lora_tranche2_signoff_test.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_lora_tranche2_signoff_pack_v1.py"),
            "--reports-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lora_tranche2_signoff_pack_v1"
    assert doc["gates"]["sweep_best_id"] == "bench_4x40"
    assert doc["recommendation"]["vision_20x200"] == "WATCH"
