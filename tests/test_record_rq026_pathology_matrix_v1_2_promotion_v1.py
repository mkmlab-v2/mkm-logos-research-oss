"""RQ-026 pathology matrix v1_2 default promotion."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "scripts/run_sasang_temperament_agents_sim_stub_v1.py"
PROMO = ROOT / "scripts/record_rq026_pathology_matrix_v1_2_promotion_v1.py"
V1_2 = ROOT / "experiments/sasang_temperament_agents_v1/specs/pathology_transition_matrix_v1_2.json"


def test_sim_default_matrix_is_v1_2() -> None:
    text = SIM.read_text(encoding="utf-8")
    assert "pathology_transition_matrix_v1_2.json" in text
    assert text.index("pathology_transition_matrix_v1_2.json") < text.find("DEFAULT_MATRIX_BASELINE")


def test_matrix_v1_2_promotion_record() -> None:
    proc = subprocess.run(
        [sys.executable, str(PROMO)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = ROOT / "docs/final/artifacts/rq026_pathology_matrix_v1_2_btrack_promotion_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("promoted_matrix_version") == "1.2.0"
    assert V1_2.name in doc.get("promoted_matrix", "")
