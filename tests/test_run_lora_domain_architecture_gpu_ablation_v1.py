from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_run_lora_domain_architecture_gpu_ablation_dry_run() -> None:
    out = ROOT / "reports" / "tmp_lora_gpu_ablation_dry_run.json"
    if out.exists():
        out.unlink()
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_lora_domain_architecture_gpu_ablation_v1.py"),
            "--dry-run",
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
    assert doc["schema"] == "lora_domain_architecture_gpu_ablation_v1"
    assert doc["status"] == "skipped"
    assert len(doc["scenarios"]) == 3
