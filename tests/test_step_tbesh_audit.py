"""STEP TBESH audit index (fixture + optional integration)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.audit_atoms_step_lexicon import build_tbesh_norm_index

REPO = Path(__file__).resolve().parents[1]


def test_build_tbesh_norm_index_fixture(tmp_path: Path):
    tb = tmp_path / "tb.txt"
    tb.write_text(
        "eStrong#\tdStrong\tuStrong\tHebrew\tTransliteration\tMorph\tGloss\tMeaning\n"
        "H0001\tH0001 =\tH0001G\tאָב\tav\tH:N-M\tfather\tx\n",
        encoding="utf-8",
    )
    idx = build_tbesh_norm_index(tb)
    assert idx.get("אב") == ["H1"]


@pytest.mark.skipif(
    not (
        REPO / "vault/external_lexicon/sources/stepbible-data/Lexicons"
    ).exists(),
    reason="STEPBible data not present",
)
def test_audit_script_runs():
    tb = list((REPO / "vault/external_lexicon/sources/stepbible-data/Lexicons").glob("TBESH*.txt"))
    if not tb:
        pytest.skip("TBESH file missing")
    out = REPO / "reports/constitution/btrack_pilot/_step_audit_test_out.json"
    r = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/audit_atoms_step_lexicon.py"),
            "--tbesh",
            str(tb[0]),
            "--out-summary",
            str(out),
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data.get("schema") == "master_atoms_step_audit_summary_v1"
    assert "coverage" in data
