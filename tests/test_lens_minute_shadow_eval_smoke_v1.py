# -*- coding: utf-8 -*-
"""Smoke: lens minute shadow eval builder writes schema-compliant JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.run_lens_minute_shadow_eval_smoke_v1 import build_report  # noqa: E402


def test_build_report_schema_fields():
    doc = build_report(bars=3, interval_minutes=5, asset_id="TEST")
    assert doc["schema"] == "lens_minute_shadow_eval_v1"
    assert doc["shadow_only"] is True
    assert doc["no_trading_action"] is True
    assert doc["bar_interval_minutes"] == 5
    assert len(doc["rows"]) == 3
    assert doc["rows"][0]["lens_minute_snapshot"]["logos"]["interpretation_snippet"].startswith("[NON_GATING]")


def test_schema_file_matches_repo_contract(tmp_path: Path):
    schema_path = _REPO / "docs/final/artifacts/schemas/lens_minute_shadow_eval_v1.schema.json"
    raw = json.loads(schema_path.read_text(encoding="utf-8"))
    assert raw["properties"]["schema"]["const"] == "lens_minute_shadow_eval_v1"
