# @MKM12-METADATA
# Type: Logic
# Purpose: Regression for myeongni independent lens v0 artifact + runner exit 0.
# Keywords: myeongni, lens, b-track

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_CONTRACT = _ROOT / "docs" / "final" / "artifacts" / "MYEONGNI_INDEPENDENT_LENS_V0_CONTRACT.json"
_RUNNER = _ROOT / "scripts" / "run_lens_myeongni.py"
_ARTIFACT = _ROOT / "docs" / "final" / "artifacts" / "myeongni_independent_lens_latest.json"


def test_contract_meta_json() -> None:
    assert _CONTRACT.is_file()
    doc = json.loads(_CONTRACT.read_text(encoding="utf-8"))
    assert doc.get("artifact_schema") == "myeongni_independent_lens_v0"
    assert "scripts/run_lens_myeongni.py" in doc.get("runner", "")


def test_runner_emits_valid_payload(tmp_path: Path) -> None:
    out = tmp_path / "lens_out.json"
    cp = subprocess.run(
        [sys.executable, str(_RUNNER), "--output", str(out)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "myeongni_independent_lens_v0"
    assert doc.get("lens_id") == "myeongni"
    assert doc.get("hypothesis_tier") == "B"
    assert doc.get("boundary_ack") is True
    scores = doc.get("scores") or {}
    assert -1.0 <= float(scores.get("direction_score", 0)) <= 1.0
    assert 0.0 <= float(scores.get("confidence", 0)) <= 1.0
    mso = doc.get("myeongri_stream_outputs") or {}
    assert isinstance(mso.get("rationale"), str) and mso["rationale"].strip()
    prov = doc.get("provenance") or {}
    assert prov.get("source")

    q = doc.get("myeongni_b_track_quant_block_v0") or {}
    assert q.get("schema") == "myeongni_b_track_quant_block_v0"
    assert q.get("status") in ("ok", "insufficient_day_stem")
    mass = q.get("five_element_mass_vector_v0") or {}
    assert len(mass) == 5
    assert abs(sum(float(mass[k]) for k in mass) - 1.0) < 1e-4


@pytest.mark.skipif(not _ARTIFACT.is_file(), reason="artifact not generated yet")
def test_checked_in_artifact_matches_schema_if_present() -> None:
    doc = json.loads(_ARTIFACT.read_text(encoding="utf-8"))
    assert doc.get("schema") == "myeongni_independent_lens_v0"
