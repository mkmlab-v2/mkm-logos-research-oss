#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from scripts.build_logos_golden_200_anchor_registry_v1 import build_registry, validate_hub_spoke_contract

ROOT = Path(__file__).resolve().parents[1]


def test_golden_200_registry_build_contract():
    doc = build_registry()
    assert doc["schema"] == "logos_golden_200_anchor_registry_v1"
    assert doc["max_slots"] == 200
    assert len(doc["entries"]) >= 4
    assert "31k" in doc["scope_ko"] or "200" in doc["scope_ko"]
    for entry in doc["entries"]:
        assert not validate_hub_spoke_contract(entry)
        contract = entry["hub_spoke_contract"]
        assert contract["forced_fit_forbidden"] is True
        assert len(entry["primary_verse_refs"]) <= contract["max_verse_refs"]


def test_golden_200_registry_written_artifact():
    out = ROOT / "docs/final/artifacts/logos_golden_200_anchor_registry_v1_latest.json"
    if not out.is_file():
        return
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["entries"][0]["hub_spoke_contract"]["send_gate"] == "HOLD"
