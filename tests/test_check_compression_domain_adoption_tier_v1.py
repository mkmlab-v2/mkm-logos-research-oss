"""Regression for compression domain adoption tier matrix gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs" / "final" / "artifacts" / "compression_domain_adoption_tier_matrix_v1.json"
SCRIPT = ROOT / "scripts" / "check_compression_domain_adoption_tier_v1.py"


def test_matrix_schema_and_tiers():
    doc = json.loads(MATRIX.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_domain_adoption_tier_matrix_v1"
    tier_ids = [t["tier_id"] for t in doc["adoption_tiers"]]
    assert tier_ids == ["adopt_ok", "adopt_limited", "adopt_not_recommended"]
    assert len(doc["four_enterprise_criteria"]) == 4
    assert len(doc["hardening_roadmap"]) == 3


def test_check_script_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--stdout-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
