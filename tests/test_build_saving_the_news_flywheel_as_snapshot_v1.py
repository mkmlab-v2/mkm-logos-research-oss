from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "flywheel",
        ROOT / "scripts/build_saving_the_news_flywheel_as_snapshot_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_forbidden_claims_present() -> None:
    mod = _load()
    doc = mod.build_snapshot()
    claims = doc.get("forbidden_claims") or []
    assert any("LOGOS-CAP" in c for c in claims)
    assert doc.get("ready_for_external_send") is False
