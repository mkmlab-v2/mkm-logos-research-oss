"""PersonaDiary Lovable DoD SSOT + bundle smoke."""
from __future__ import annotations

import json
from pathlib import Path


def test_dod_ssot_has_ten_gates():
    path = Path(__file__).resolve().parents[1] / "docs/final/artifacts/personadiary_lovable_dod_v1_latest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema"] == "personadiary_lovable_dod_v1"
    assert len(data["gates"]) == 10
    assert data["recommended_default"] == "tier_0"
    ids = {g["id"] for g in data["gates"]}
    assert ids == {f"G{i:02d}" for i in range(1, 11)}
