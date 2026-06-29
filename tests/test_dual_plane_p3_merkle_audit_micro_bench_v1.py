from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/dual_plane_p3_merkle_audit_crosswalk_v1.json"
SCRIPT = ROOT / "scripts/run_dual_plane_p3_merkle_audit_micro_bench_v1.py"
SIZE = ROOT / "scripts/analyze_mkm_universal_root_export_size_v1.py"


def test_merkle_detects_tamper():
    from scripts.run_dual_plane_p3_merkle_audit_micro_bench_v1 import (
        apply_tamper,
        merkle_post_passes,
    )

    sample = {"canonical_tokens": ["a", "b", "c"], "tampered": True, "tamper_index": 1, "tamper_value": "z"}
    stream = apply_tamper(sample)
    assert merkle_post_passes(stream, sample["canonical_tokens"]) is False


def test_run_bench_post_detects_all_tamper():
    from scripts.run_dual_plane_p3_merkle_audit_micro_bench_v1 import run_bench

    fixture = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
    report = run_bench(fixture)
    assert report["metrics"]["post_merkle_tamper_undetected_rate"] == 0.0
    assert report["metrics"]["raw_tamper_undetected_rate"] > 0.0
    assert report["metrics"]["collapsed_combined_score"] is None


def test_p3_cli_and_export_size_audit():
    out = ROOT / "reports/_tmp_p3_bench.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    proc2 = subprocess.run([sys.executable, str(SIZE)], cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert proc2.returncode == 0, proc2.stderr or proc2.stdout
