"""paradigm_factcheck_v1.json — minimal schema contract."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts/paradigm_factcheck_v1.json"


def test_paradigm_factcheck_v1_exists_and_layers() -> None:
    assert ART.is_file(), f"missing SSOT: {ART}"
    doc = json.loads(ART.read_text(encoding="utf-8"))
    assert doc.get("schema") == "paradigm_factcheck_v1"
    layers = doc.get("layers")
    assert isinstance(layers, dict)
    for key in ("implemented_fact", "implemented_not_wired", "compartmentalized", "vision_hypo"):
        assert isinstance(layers.get(key), list) and len(layers[key]) >= 1
    assert doc.get("promotion_pointers", {}).get("human_signoff_required") is True
