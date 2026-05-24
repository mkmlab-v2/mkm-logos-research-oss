"""Profile registry refresh — dry structure check."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_profile_registry_schema() -> None:
    reg = json.loads(
        (ROOT / "data/personadiary/profile_registry_v1.json").read_text(encoding="utf-8")
    )
    assert reg["schema"] == "personadiary_profile_registry_v1"
    assert "commander" in reg["profiles"]
    p = ROOT / reg["profiles"]["commander"]["profile_json"]
    assert p.is_file()
