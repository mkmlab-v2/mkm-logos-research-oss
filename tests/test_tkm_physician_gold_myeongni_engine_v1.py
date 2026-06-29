"""TKM physician_gold engine myeongni report materialization."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_mod(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_birth_anchor_resolve_physician_gold() -> None:
    mod = _load_mod("birth", "scripts/tkm_physician_gold_birth_profile_v1.py")
    capture = {
        "schema": "clinic_constitution_mvp_capture_v1",
        "encounter": {"ref_token": "ENC-PHYSICIAN-GOLD-AUTO-01"},
        "modalities_present": {"birth_profile": True},
    }
    anchor = mod.resolve_birth_anchor(capture)
    assert anchor is not None
    assert anchor.get("year") == 1972


def test_sidecar_prefers_engine_over_stub() -> None:
    sidecar = _load_mod("sidecar", "scripts/tkm_encounter_sequence_myeongni_sidecar_v1.py")
    engine_dir = ROOT / "reports/myeongni_physician_gold_engine"
    engine_dir.mkdir(parents=True, exist_ok=True)
    engine_path = engine_dir / "ENC-PHYSICIAN-GOLD-AUTO-99_v1_latest.json"
    engine_path.write_text(
        json.dumps(
            {
                "meta": {"engine_built": True, "stub": False, "research_only": True},
                "birth_engine": {"calculation_method": "test"},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    record = {
        "encounter": {"ref_token": "ENC-PHYSICIAN-GOLD-AUTO-99"},
        "turns": [{"modalities_present": {"birth_profile": True}}],
    }
    ref = sidecar.resolve_myeongni_report_ref(record)
    assert ref is not None
    assert "myeongni_physician_gold_engine" in ref.replace("\\", "/")
    assert sidecar._is_engine_report(ref) is True


def test_materialize_dry_run() -> None:
    mod = _load_mod("mat", "scripts/materialize_tkm_physician_gold_myeongni_engine_v1.py")
    doc = mod.run(dry_run=True)
    assert int(doc.get("capture_count") or 0) >= 1
