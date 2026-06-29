"""fABBA ngram_lut sidecar registration smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_ngram_lut_registration_schema() -> None:
    out = ROOT / "reports/prophecy_fabba_ngram_lut_sidecar_registration_v1_latest.json"
    if not out.is_file():
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/register_prophecy_fabba_ngram_lut_sidecar_v1.py")],
            cwd=str(ROOT),
            timeout=600,
        )
        assert proc.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "prophecy_fabba_ngram_lut_sidecar_registration_v1"
    reg = doc.get("registration") or {}
    assert reg.get("primary_sidecar_arm") == "fabba_sidecar_ngram_lut"
    assert reg.get("vote_participation") == "none"
    assert reg.get("non_gating") is True
    assert doc.get("lut_ablation_smoke", {}).get("feature_parity_ok") is True
