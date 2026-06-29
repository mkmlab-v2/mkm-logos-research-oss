"""Universal Root Gate Spec v1 — structural validation + gate eval smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SPEC = REPO / "docs/final/artifacts/UNIVERSAL_ROOT_GATE_SPEC_V1.json"
SCHEMA = REPO / "docs/final/schemas/universal_root_gate_spec_v1.schema.json"
CHECKER = REPO / "scripts/check_universal_root_gate_spec_v1.py"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True)


def test_spec_file_exists_and_schema_const():
    assert SPEC.is_file()
    doc = json.loads(SPEC.read_text(encoding="utf-8"))
    assert doc["schema"] == "universal_root_gate_spec_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["track_a_promotion_forbidden"] is True
    assert "layer_a" in doc["layers"]
    assert doc["promotion_gates"]["research_ready_decision"] == "HOLD"


def test_checker_smoke():
    r = _run([sys.executable, str(CHECKER)])
    assert r.returncode == 0, r.stderr
    out = REPO / "reports/universal_root_gate_eval_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "universal_root_gate_eval_v1"
    assert doc["evaluation"]["research_ready_decision"] in {"HOLD", "B_TRACK_RESEARCH_READY"}


@pytest.mark.skipif(not SCHEMA.is_file(), reason="schema missing")
def test_spec_jsonschema_when_available():
    jsonschema = pytest.importorskip("jsonschema")
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(instance=spec, schema=schema)


def test_enforce_promotion_gates_tracks_enabled_planes():
    r = _run([sys.executable, str(CHECKER), "--enforce-promotion-gates"])
    out = REPO / "reports/universal_root_gate_eval_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    all_ok = doc["evaluation"]["all_enabled_planes_ok"]
    assert r.returncode == (0 if all_ok else 1)
    assert doc["send_gate"] == "HOLD"
