from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/audio/templates/mkm_commercial_csharp_v1.logic_template_contract_v1.json"
MAP = ROOT / "data/audio/maps/mkm_commercial_csharp_v1.example.json"
CHECK = ROOT / "scripts/audio/check_logic_template_contract_v1.py"


def test_contract_schema_and_required_fields():
    doc = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert doc["schema"] == "logic_template_contract_v1"
    assert doc["template_id"] == "mkm_commercial_csharp_v1"
    assert doc["instrument_map_path"] == "data/audio/maps/mkm_commercial_csharp_v1.example.json"
    assert len(doc["tracks"]) == 4
    assert doc["session"]["default_bpm"] == 92


def test_contract_aligns_with_instrument_map():
    from scripts.audio.check_logic_template_contract_v1 import load_contract, validate_alignment
    from scripts.audio.logic_instrument_map_v1_lib import load_instrument_map

    contract = load_contract(CONTRACT)
    inst = load_instrument_map(MAP)
    errors = validate_alignment(contract, inst)
    assert errors == [], errors


def test_check_script_exit_0(tmp_path: Path):
    report = tmp_path / "report.json"
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) if not prev else f"{ROOT}{__import__('os').pathsep}{prev}"
    r = subprocess.run(
        [sys.executable, str(CHECK), "--contract", str(CONTRACT), "--export-report", str(report)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(report.read_text(encoding="utf-8"))
    assert doc["ok"] is True
