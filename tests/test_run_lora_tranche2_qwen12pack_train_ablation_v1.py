from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_run_lora_tranche2_qwen12pack_train_ablation_v1_dry_run() -> None:
    out = ROOT / "reports" / "tmp_lora_tranche2_qwen12pack_ablation_test.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_lora_tranche2_qwen12pack_train_ablation_v1.py"),
            "--dry-run",
            "--train-steps",
            "2",
            "--rows-per-pack-cap",
            "4",
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lora_tranche2_qwen12pack_train_ablation_v1"
    assert doc["architecture_target"] == "hier_12x75_hybrid"
    assert doc["pack_count"] == 12
