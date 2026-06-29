"""RQ-026 pathology matrix v1_1 default promotion."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMO = ROOT / "scripts/record_rq026_pathology_matrix_v1_1_promotion_v1.py"
V1_1 = ROOT / "experiments/sasang_temperament_agents_v1/specs/pathology_transition_matrix_v1_1.json"


def test_v1_1_promotion_artifact_still_valid() -> None:
    proc = subprocess.run(
        [sys.executable, str(PROMO)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = ROOT / "docs/final/artifacts/rq026_pathology_matrix_v1_1_btrack_promotion_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("promoted_matrix_version") == "1.1.0"
    assert V1_1.name in doc.get("promoted_matrix", "")
