"""Tests for en_tech OOV must_keep patch builder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OOV = ROOT / "reports/constitution/btrack_pilot/comp_en_tech_oov_coverage_from_cpu_freeze_v1.json"
OUT = ROOT / "docs/final/artifacts/en_tech_oov_must_keep_patch_v1.json"


def test_build_en_tech_oov_must_keep_patch_v1() -> None:
    assert OOV.is_file()
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_en_tech_oov_must_keep_patch_v1.py"),
            "--out-json",
            str(OUT),
            "--min-case-frequency",
            "75",
            "--max-tokens",
            "32",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    assert OUT.is_file()
    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "en_tech_oov_must_keep_patch_v1"
    assert doc.get("research_only") is True
    tokens = doc.get("must_keep_tokens") or []
    assert "checksum" in tokens
    assert "sha256" in tokens
    assert len(tokens) <= 32


def test_poc_accepts_must_keep_patch_json() -> None:
    assert OUT.is_file()
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_en_tech_semantic_gpu_poc_v1.py"),
            "--max-cases",
            "1",
            "--skip-gpu-semantic",
            "--must-keep-patch-json",
            str(OUT),
            "--out-json",
            "reports/constitution/btrack_pilot/comp_en_tech_semantic_gpu_poc_oov_patch_smoke_v1_latest.json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    out = ROOT / "reports/constitution/btrack_pilot/comp_en_tech_semantic_gpu_poc_oov_patch_smoke_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc.get("must_keep_token_count", 0) > len({"checksum"})
