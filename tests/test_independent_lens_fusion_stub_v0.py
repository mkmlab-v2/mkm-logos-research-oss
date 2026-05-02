# @MKM12-METADATA
# Type: Logic
# Purpose: Regression for independent lens fusion stub v0 reporter.
# Keywords: fusion_stub, independent_lens, comparison

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_RUNNER = _ROOT / "scripts" / "report_independent_lens_fusion_stub_v0.py"
_CONTRACT = _ROOT / "docs" / "final" / "artifacts" / "INDEPENDENT_LENS_FUSION_STUB_V0_CONTRACT.json"


def test_contract_file_exists() -> None:
    assert _CONTRACT.is_file()
    doc = json.loads(_CONTRACT.read_text(encoding="utf-8"))
    assert doc.get("artifact_schema") == "independent_lens_fusion_stub_v0"
    assert doc.get("runner") == "scripts/report_independent_lens_fusion_stub_v0.py"


def test_runner_emits_fusion_summary(tmp_path: Path) -> None:
    out = tmp_path / "fusion.json"
    cp = subprocess.run(
        [sys.executable, str(_RUNNER), "--output", str(out)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "independent_lens_fusion_stub_v0"
    assert doc.get("hypothesis_tier") == "B"
    assert doc.get("boundary_ack") is True
    inputs = doc.get("inputs") or []
    assert len(inputs) == 3
    cs = doc.get("consensus") or {}
    assert 0.0 <= float(cs.get("agreement_rate", 0.0)) <= 1.0
    assert -1.0 <= float(cs.get("consensus_score", 0.0)) <= 1.0
    assert doc.get("version") == "0.2.0"
    csum = doc.get("conflict_summary") or {}
    assert isinstance(csum.get("conflict_narrative_guarded"), str)
    assert len(csum.get("conflict_narrative_guarded", "")) >= 10
    assert isinstance(csum.get("minority_lens_ids"), list)
    assert isinstance(csum.get("logos_evidence_verse_ids"), list)
    assert csum.get("narrative_policy")
