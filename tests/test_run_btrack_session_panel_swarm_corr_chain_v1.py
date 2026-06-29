# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_CHAIN = _ROOT / "scripts" / "run_btrack_session_panel_swarm_corr_chain_v1.py"
_JSONL = _ROOT / "tests" / "fixtures" / "btrack_swarm_smoke_v1.jsonl"
_OHLCV = _ROOT / "tests" / "fixtures" / "btrack_join_ohlcv_smoke_v1.csv"


def test_swarm_sasang_corr_chain_smoke(tmp_path: Path) -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(_CHAIN),
            "--date-from",
            "2024-06-12",
            "--date-to",
            "2024-06-14",
            "--calendar-mode",
            "all",
            "--out-dir",
            str(tmp_path),
            "--tag",
            "pytest_smoke",
            "--swarm-jsonl",
            str(_JSONL),
            "--ohlcv-csv",
            str(_OHLCV),
            "--min-pairs",
            "3",
            "--no-copy-latest",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    eval_json = tmp_path / "btrack_swarm_sasang_correlation_pytest_smoke.json"
    assert eval_json.is_file()
    doc = json.loads(eval_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "btrack_swarm_sasang_correlation_v1"
    assert doc.get("research_only") is True
    assert doc.get("verdict", {}).get("track_a_promotion") is False
    assert doc.get("verdict", {}).get("fusion_pipeline_merge_allowed") is False
