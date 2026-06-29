# -*- coding: utf-8 -*-
"""Smoke: gwangmyeong B2B training spec barrier audit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_b2b_barrier_audit_exit_zero(tmp_path: Path) -> None:
    from scripts import check_gwangmyeong_baekje_b2b_training_spec_v1 as mod

    out = tmp_path / "audit.json"
    rc = mod.main.__wrapped__ if hasattr(mod.main, "__wrapped__") else None
    import sys

    argv = [
        "check_gwangmyeong_baekje_b2b_training_spec_v1.py",
        "--out",
        str(out),
    ]
    old = sys.argv
    try:
        sys.argv = argv
        code = mod.main()
    finally:
        sys.argv = old

    assert code == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["ok"] is True
    assert data["audit_status"] == "PASS"
    assert len(data["barriers"]) == 3


def test_b2b_spec_file_exists() -> None:
    path = ROOT / "docs/final/artifacts/gwangmyeong_baekje_b2b_training_spec_v1.json"
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema"] == "gwangmyeong_baekje_b2b_training_spec_v1"
    assert data["governance"]["send_gate"] == "HOLD"


def test_b2b_solapi_dry_build_exit_zero(tmp_path: Path) -> None:
    from scripts import build_gwangmyeong_baekje_b2b_solapi_dry_v1 as mod

    out = tmp_path / "solapi_dry.json"
    import sys

    argv = ["build_gwangmyeong_baekje_b2b_solapi_dry_v1.py", "--out", str(out)]
    old = sys.argv
    try:
        sys.argv = argv
        code = mod.main()
    finally:
        sys.argv = old

    assert code == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["ok"] is True
    assert data["live_send"] is False
    assert len(data["templates_dry"]) == 3
