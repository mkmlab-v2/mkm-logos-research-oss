"""Concept bridge registry v1."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_logos_concept_bridge_registry_v1.py"
SEMI = ROOT / "scripts/build_logos_concept_bridge_semiconductor_poc_v1.py"
COV = ROOT / "scripts/build_logos_concept_bridge_covenant_crisis_poc_v1.py"


def test_registry_lists_two_bridges(tmp_path: Path) -> None:
    semi = tmp_path / "semi.json"
    cov = tmp_path / "cov.json"
    subprocess.run([sys.executable, str(SEMI), "--output-json", str(semi)], cwd=str(ROOT), check=True)
    subprocess.run([sys.executable, str(COV), "--output-json", str(cov)], cwd=str(ROOT), check=True)
    out = tmp_path / "registry.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--output-json",
            str(out),
            "--bridge-json",
            str(semi),
            "--bridge-json",
            str(cov),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["bridge_count"] == 2
    assert doc["governance_warning_zero_human"] is True
