#!/usr/bin/env python3
"""Expanded locked_eval on existing A-code Qwen 12-pack adapters (no retrain).

B-track / hier_12x75_hybrid — not bench 4×40, not Track A GO.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ABLATION = ROOT / "reports/lora_tranche2_qwen12pack_acode_train_ablation_latest.json"
DEFAULT_OUT = ROOT / "reports/lora_tranche2_qwen12pack_acode_locked_eval_expanded_latest.json"


def main() -> int:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/run_lora_tranche2_qwen4pack_locked_eval_expanded_v1.py"),
        "--ablation-json",
        str(DEFAULT_ABLATION),
        "--out-json",
        str(DEFAULT_OUT),
        "--schema",
        "lora_tranche2_qwen12pack_acode_locked_eval_expanded_v1",
        "--architecture-lane",
        "hier_12x75_hybrid",
        *sys.argv[1:],
    ]
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
