"""Smoke tests for Nemotron Kaggle kernel bundle (no GPU, no push)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "data/kaggle/nvidia-nemotron-model-reasoning-challenge/kaggle_train"
TRAIN_SCRIPT = BUNDLE / "nemotron_qlora_train_v1.py"
BUILDER = ROOT / "scripts/build_kaggle_nemotron_kernel_bundle_v1.py"


def test_kernel_metadata_exists() -> None:
    meta = json.loads((BUNDLE / "kernel-metadata.json").read_text(encoding="utf-8"))
    assert meta["competition_sources"] == ["nvidia-nemotron-model-reasoning-challenge"]
    assert meta["enable_gpu"] is True
    assert meta["is_private"] is True
    assert meta["kernel_type"] == "script"
    assert meta["code_file"] == "nemotron_qlora_train_v1.py"

    nb = ROOT / "data/kaggle/nvidia-nemotron-model-reasoning-challenge/kaggle_train_nb"
    nb_meta = json.loads((nb / "kernel-metadata.json").read_text(encoding="utf-8"))
    assert nb_meta["kernel_type"] == "notebook"
    assert nb_meta["id"] == "familyunion/nemotron-qlora-private-train-v2-notebook-t4"


def test_train_script_dry_run() -> None:
    out = ROOT / "reports/test_kaggle_nemotron_train_dryrun.json"
    proc = subprocess.run(
        [sys.executable, str(TRAIN_SCRIPT), "--dry-run", "--limit", "4", "--out-report-json", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(out.read_text(encoding="utf-8"))
    assert body["dry_run"] is True
    assert body["row_count"] == 4


def test_bundle_builder() -> None:
    out = ROOT / "reports/test_kaggle_nemotron_kernel_bundle.json"
    proc = subprocess.run(
        [sys.executable, str(BUILDER), "--out-json", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(out.read_text(encoding="utf-8"))
    assert body["schema"] == "kaggle_nemotron_kernel_bundle_v1"
    assert body["kernel_id"] == "familyunion/nemotron-qlora-private-train-v1"
