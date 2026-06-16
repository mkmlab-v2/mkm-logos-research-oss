"""[HYPO] rib55 anatomy_overlay_coord_v2 manifest extension."""
from __future__ import annotations

import json
from pathlib import Path

from scripts import build_rib55_manifest_coord_v2_v1 as build_mod
from scripts import validate_anatomy_overlay_coord_v2_v1 as validate_mod

ROOT = Path(__file__).resolve().parents[1]


def test_build_and_validate_coord_v2(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["build_rib55_manifest_coord_v2_v1.py"])
    assert build_mod.main() == 0

    manifest = json.loads(build_mod.MANIFEST.read_text(encoding="utf-8"))
    assert manifest.get("coord_spec_v2") == "anatomy_overlay_coord_v2"
    assert manifest.get("coord_v2", {}).get("r1_ablation", {}).get("angle_delta") == -5.75

    monkeypatch.setattr("sys.argv", ["validate_anatomy_overlay_coord_v2_v1.py"])
    assert validate_mod.main() == 0

    report = json.loads(validate_mod.OUT.read_text(encoding="utf-8"))
    assert report["ok"] is True
