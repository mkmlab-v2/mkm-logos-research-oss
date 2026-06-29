"""Tests for digestion blocked public claims builder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_mkm_digestion_blocked_public_claims_v1.py"
HYBRID = ROOT / "docs/final/artifacts/tier0_hybrid_ai_web_sweep_2026-06-20_digested_facts_latest.json"


def test_blocked_claims_builder_exit_zero(tmp_path: Path) -> None:
    assert HYBRID.is_file(), "run hybrid digestion chain first"
    out = tmp_path / "blocked.json"
    proc = subprocess.run(
        [sys.executable, str(BUILD), "--digested", str(HYBRID), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_digestion_blocked_public_claims_v1"
    assert doc["send_gate"] == "HOLD"
    by_id = {r["fact_id"]: r for r in doc["blocked_rows"]}
    assert by_id["hybrid_ce_collm_latency_verified"]["verification_status"] == "Right"
    assert by_id["hybrid_ce_collm_latency_verified"]["arxiv_id"] == "2411.02829"
