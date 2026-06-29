"""Smoke tests for NVIDIA local Nemotron train (dry-run only)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRAIN = ROOT / "data/nvidia/nemotron-local/nemotron_qlora_train_v1.py"


def test_local_train_dry_run() -> None:
    out = ROOT / "reports/test_nvidia_nemotron_local_train_dryrun.json"
    proc = subprocess.run(
        [sys.executable, str(TRAIN), "--dry-run", "--limit", "4", "--out-report-json", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(out.read_text(encoding="utf-8"))
    assert body["schema"] == "nvidia_nemotron_local_train_v1"
    assert body["runtime"] == "nvidia_local_wsl"
    assert body["dry_run"] is True


def test_nemotron_policy_and_wsl_bootstrap_paths_exist() -> None:
    policy = ROOT / "docs/final/artifacts/nvidia_nemotron_local_dev_policy_v1.json"
    bootstrap = ROOT / "scripts/wsl/nemotron_local_setup_and_train_v1.sh"
    invoke = ROOT / "scripts/Invoke-NvidiaNemotronLocalTrain_v1.ps1"
    readiness = ROOT / "scripts/Verify-NvidiaNemotronWslReadiness_v1.ps1"
    assert policy.is_file()
    assert bootstrap.is_file()
    assert invoke.is_file()
    assert readiness.is_file()
    doc = json.loads(policy.read_text(encoding="utf-8"))
    assert doc["schema"] == "nvidia_nemotron_local_dev_policy_v1"
    assert doc["kaggle_lane"] == "cancelled"
    raw = bootstrap.read_bytes()
    assert b"\r" not in raw, "WSL bootstrap must be LF-only (see .gitattributes *.sh eol=lf)"
