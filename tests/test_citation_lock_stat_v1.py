"""CL_stat citation lock — entropy + Wilson bound smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / "scripts/verifier/citation_lock_stat_v1.py"
ARTIFACT = REPO / "docs/final/artifacts/citation_lock_stat_eval_v1_latest.json"

sys.path.insert(0, str(REPO))

from scripts.verifier.citation_lock_stat_v1 import compute_cl_stat, shannon_entropy  # noqa: E402


def test_entropy_gate_rejects_inconsistent_samples():
    claims = [{"fuzzy_score": 0.95, "weight": 1.0}] * 5
    inconsistent = ["claim A", "claim B", "claim C", "claim D", "claim E"]
    assert shannon_entropy(inconsistent) > 0.12
    result = compute_cl_stat(claims, inconsistent)
    assert result["gate_ok"] is False
    assert result["reject_reason"] == "entropy_exceeded"


def test_cl_stat_passes_consistent_high_fuzzy_claims():
    claims = [{"fuzzy_score": 0.95, "weight": 1.0} for _ in range(8)]
    consistent = ["verified anchor set"] * 5
    result = compute_cl_stat(claims, consistent)
    assert result["gate_ok"] is True
    assert result["weighted_mean"] >= 0.85


def test_cli_default_exit_zero():
    r = subprocess.run([sys.executable, str(CLI)], cwd=str(REPO), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    doc = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert doc["schema"] == "citation_lock_stat_v1"
    assert doc["send_gate"] == "HOLD"
