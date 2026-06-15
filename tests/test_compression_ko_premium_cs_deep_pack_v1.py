"""Ko premium CS deep pack twin gate + mask preservation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE_BUILDER = ROOT / "scripts/build_compression_ko_premium_cs_deep_pack_gate_v1.py"
TEMPLATES = ROOT / "codebook/templates/zone_ko_premium_cs_templates_v1.jsonl"
GATE_ARTIFACT = ROOT / "docs/final/artifacts/compression_ko_premium_cs_deep_pack_gate_v1_latest.json"


def test_build_ko_premium_cs_deep_pack_gate_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(GATE_BUILDER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert GATE_ARTIFACT.is_file()
    doc = json.loads(GATE_ARTIFACT.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_ko_premium_cs_deep_pack_gate_v1"
    assert doc["wire_family"] == "CS_MASK"
    summary = doc["summary"]
    assert summary["exact_restore_pass_count"] == summary["case_count"] == 22
    assert summary["mean_saving_rate"] > 0.0


def test_ko_premium_cs_gate_mask_tokens_preserved() -> None:
    if not GATE_ARTIFACT.is_file():
        pytest.skip("gate artifact missing")
    doc = json.loads(GATE_ARTIFACT.read_text(encoding="utf-8"))
    for case in doc["cases"]:
        assert case.get("exact_restore_ok") is True
        assert str(case.get("wire_compact", "")).startswith("[CS_MASK:")
    rows = [json.loads(line) for line in TEMPLATES.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert all("███" in str(r["snippet"]) for r in rows[:5])
