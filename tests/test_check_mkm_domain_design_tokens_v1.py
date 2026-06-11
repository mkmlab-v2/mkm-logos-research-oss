"""Offline gate for mkm_domain_design_tokens_v1.json."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load():
    path = Path(__file__).resolve().parents[1] / "scripts" / "check_mkm_domain_design_tokens_v1.py"
    spec = importlib.util.spec_from_file_location("check_mkm_domain_design_tokens_v1", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_design_tokens_gate_passes():
    assert _load().main() == 0
