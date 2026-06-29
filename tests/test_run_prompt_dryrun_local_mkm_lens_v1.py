"""Offline contract tests for prompt_dryrun_local_mkm_lens_v1 scoring helpers."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "scripts/run_prompt_dryrun_local_mkm_lens_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("prompt_dryrun", MOD)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_score_passes_good_response():
    mod = _load()
    anchor = {"engine_inputs": {"year": 1992, "month": 3, "day": 13, "hour": 2}}
    text = (
        "1) 명리: engine_inputs 1992-03-13 [HYPO] mid profile.\n"
        "2) 사상: [HYPO] short intensity only.\n"
        "3) Logos [NON_GATING] guard.\n"
        "Final Action = WATCH"
    )
    s = mod._score(text, anchor)
    assert s["pass_heuristic"] is True


def test_resolve_profile_local_ladakh():
    mod = _load()
    prof = {
        "label": "ladakh_2021",
        "local": [2021, 1, 5, 19, 0, 0],
        "iana_tz": "Asia/Kolkata",
        "place": "ladakh",
    }
    doc = mod._resolve_profile(prof)
    assert "engine_inputs" in doc or "pillars" in doc or doc


def test_score_fails_trade_language():
    mod = _load()
    anchor = {"engine_inputs": {"year": 1992}}
    text = "매수하라 [HYPO] [NON_GATING] 1992 WATCH"
    s = mod._score(text, anchor)
    assert s["pass_heuristic"] is False
    assert s["forbidden_trade_language"] is True
