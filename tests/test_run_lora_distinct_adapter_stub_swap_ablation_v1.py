from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_run_lora_distinct_adapter_stub_swap_ablation_dry_run() -> None:
    out = ROOT / "reports" / "tmp_lora_stub_swap_dry_run.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_lora_distinct_adapter_stub_swap_ablation_v1.py"),
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
    assert doc["status"] == "skipped"
    assert doc["schema"] == "lora_distinct_adapter_stub_swap_ablation_v1"
