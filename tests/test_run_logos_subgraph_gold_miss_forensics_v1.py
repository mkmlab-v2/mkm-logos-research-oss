"""Smoke test for subgraph gold miss forensics v1."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORENSICS = ROOT / "scripts/run_logos_subgraph_gold_miss_forensics_v1.py"


def test_gold_miss_forensics_smoke(tmp_path: Path) -> None:
    out = tmp_path / "forensics.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(FORENSICS),
            "--skip-gold-eval",
            "--out",
            str(out),
            "--miss-ids",
            "q05,q12",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_subgraph_gold_miss_forensics_v1"
    assert doc["send_gate"] == "HOLD"
    assert len(doc["rows"]) == 2
