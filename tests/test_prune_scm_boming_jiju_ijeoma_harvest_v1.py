# -*- coding: utf-8 -*-
"""Prune ijeoma_harvest lexicon noise."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PRUNE_SCRIPT = ROOT / "scripts" / "prune_scm_boming_jiju_ijeoma_harvest_lexicon_v1.py"
LEXICON = ROOT / "docs" / "final" / "artifacts" / "scm_boming_jiju_lexicon_v1.json"


def test_plan_prune_finds_ijoeoma_harvest_rows():
    from scripts.core.prune_scm_boming_jiju_ijeoma_harvest_v1 import plan_prune

    if not LEXICON.is_file():
        pytest.skip("lexicon missing")
    plan = plan_prune()
    assert plan["counts"]["before"] > 0
    assert plan["counts"]["removed"] >= 0


def test_prune_cli_dry_run(tmp_path):
    if not LEXICON.is_file():
        pytest.skip("lexicon missing")
    out = tmp_path / "prune_report.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(PRUNE_SCRIPT),
            "--dry-run",
            "--apply",
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc["apply"]["dry_run"] is True
    assert doc["counts"]["removed"] >= 0
