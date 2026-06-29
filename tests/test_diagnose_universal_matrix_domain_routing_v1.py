"""Smoke: universal matrix routing diagnosis on synthetic stress lane subset."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_diagnose_routing_smoke(tmp_path: Path) -> None:
    matrix = ROOT / "docs/final/artifacts/UNIVERSAL_COMPRESSION_BENCH_MATRIX_INPUT_V1.json"
    if not matrix.is_file():
        return
    out = tmp_path / "routing_diag.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/diagnose_universal_matrix_domain_routing_v1.py"),
            "--matrix-input",
            str(matrix),
            "--out-json",
            str(out),
            "--lane-id",
            "en_tech_spec_stress_v1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("research_only") is True
    lanes = doc["profiles"]["default_shards"]["lanes"]
    assert "en_tech_spec_stress_v1" in lanes
    assert lanes["en_tech_spec_stress_v1"]["case_count"] > 0


def test_build_router_sharp_shards_smoke(tmp_path: Path) -> None:
    out_dir = tmp_path / "sharp_shards"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_router_sharp_v1_shards_v1.py"),
            "--out-dir",
            str(out_dir),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert list(out_dir.glob("zone_*.json"))
