# @MKM12-METADATA
# Type: Logic
# Purpose: Fusion JSON → advanced_input → 명리 렌즈 v1 브리지 회귀.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def test_fusion_bridge_build_advanced_payload_structure() -> None:
    from myeongni_lens_v1.fusion_bridge import (
        build_advanced_input_from_fusion,
        unwrap_fusion_payload,
    )
    from scripts.myeongri_complete_fusion import MyeongriCompleteFusion

    fus = MyeongriCompleteFusion().calculate_complete_fusion(
        2000, 6, 15, 12, is_solar=True, is_male=True
    )
    assert unwrap_fusion_payload(fus) is not None
    adv = build_advanced_input_from_fusion(fus)
    assert adv.get("schema") == "myeongni_lens_advanced_input_v1"
    assert adv["pillars"]["year"]
    assert isinstance(adv["dayun"], list) and len(adv["dayun"]) >= 1
    assert isinstance(adv["sajeong_interpolation"], dict)
    assert "year" in adv["sajeong_interpolation"]


def test_commander_style_wrapper_unwrap() -> None:
    from myeongni_lens_v1.fusion_bridge import unwrap_fusion_payload
    from scripts.myeongri_complete_fusion import MyeongriCompleteFusion

    fus = MyeongriCompleteFusion().calculate_complete_fusion(
        2000, 6, 15, 12, is_solar=True, is_male=True
    )
    wrapped = {"schema": "stub_commander", "full_fusion_payload": fus}
    assert unwrap_fusion_payload(wrapped) == fus


def test_lens_runner_advanced_from_fusion_json(tmp_path: Path) -> None:
    from scripts.myeongri_complete_fusion import MyeongriCompleteFusion

    fus = MyeongriCompleteFusion().calculate_complete_fusion(
        2000, 6, 15, 12, is_solar=True, is_male=True
    )
    p = tmp_path / "fusion.json"
    p.write_text(json.dumps(fus, ensure_ascii=False), encoding="utf-8")
    runner = _ROOT / "scripts/run_lens_myeongni.py"
    out = tmp_path / "lens.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(runner),
            "--emit-schema",
            "v1",
            "--advanced-from-fusion-json",
            str(p),
            "--allow-fallback",
            "--output",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "myeongni_independent_lens_v1"
    coord = (doc.get("advanced") or {}).get("coordinator") or {}
    assert len(coord.get("school_signals") or []) >= 1


def test_run_lens_recommended_emits_v1(tmp_path: Path) -> None:
    runner = _ROOT / "scripts/run_lens_myeongni.py"
    out = tmp_path / "lens_rec.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(runner),
            "--recommended",
            "--output",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    import json

    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "myeongni_independent_lens_v1"
    inp = (doc.get("advanced") or {}).get("input_summary") or {}
    prov = inp.get("provenance") or {}
    assert prov.get("recommended_mode")


def test_emit_cli_writes_advanced(tmp_path: Path) -> None:
    emit = _ROOT / "scripts/emit_myeongni_lens_advanced_from_fusion_v1.py"
    out = tmp_path / "adv.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(emit),
            "--compute-birth",
            "--birth-year",
            "2000",
            "--birth-month",
            "6",
            "--birth-day",
            "15",
            "--birth-hour",
            "12",
            "--is-solar",
            "--is-male",
            "--output",
            str(out),
            "--compact",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "myeongni_lens_advanced_input_v1"
