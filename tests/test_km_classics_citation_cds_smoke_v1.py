"""Stage C: KM classics citation + CDS chain + policy smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "scripts/run_km_classics_citation_cds_smoke_v1.py"
VALIDATE = ROOT / "scripts/validate_patient_care_bundle_against_policy_v1.py"


@pytest.mark.skipif(not SMOKE.is_file(), reason="smoke script missing")
def test_km_classics_citation_cds_smoke_cli(tmp_path: Path) -> None:
    out = tmp_path / "smoke.json"
    cp = subprocess.run(
        [sys.executable, str(SMOKE), "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["classic_refs_count"] >= 1


@pytest.mark.skipif(not VALIDATE.is_file(), reason="validate script missing")
def test_policy_rejects_invalid_classic_refs(tmp_path: Path) -> None:
    bundle = tmp_path / "bad_bundle.json"
    bundle.write_text(
        json.dumps(
            {
                "schema": "patient_care_bundle_v1",
                "version": "1.0.0",
                "bundle_id": "test",
                "generated_at_utc": "2026-06-14T12:00:00Z",
                "provenance": {
                    "generator_id": "test",
                    "generator_version": "0",
                    "classic_refs": [
                        {
                            "source_id": "kmc-deadbeef",
                            "work": "bad",
                            "retrieval_query": "q",
                            "citation_valid": False,
                        }
                    ],
                },
                "boundary_contract": {
                    "physician_final_authority": True,
                    "clinical_slots_separate_from_lens": True,
                    "myeongni_hypo_only": True,
                    "logos_non_gating_only": True,
                },
                "clinical_soap_v1": {
                    "subjective": {"text": "s"},
                    "objective": {"text": "o"},
                    "assessment": {"text": "a"},
                    "plan": {"text": "p"},
                },
                "patient_slots": [],
                "disclaimers": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    cp = subprocess.run(
        [sys.executable, str(VALIDATE), "--bundle-json", str(bundle)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode != 0
    assert "citation_valid" in cp.stderr
