"""B4: prescription claim requires classic_refs policy gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATE = ROOT / "scripts/validate_patient_care_bundle_against_policy_v1.py"
POLICY = ROOT / "docs/final/artifacts/patient_care_bundle_generation_policy_v1.default.json"


def _minimal_bundle(*, with_refs: bool) -> dict:
    bundle = {
        "schema": "patient_care_bundle_v1",
        "bundle_id": "test-b4",
        "clinical_soap_v1": {
            "subjective": {"text": "요약"},
            "objective": {"text": "소견"},
            "assessment": {"text": "평가"},
            "plan": {"text": "보존탕 복용 권고"},
        },
        "patient_slots": [],
        "disclaimers": [],
        "provenance": {},
    }
    if with_refs:
        bundle["provenance"]["classic_refs"] = [
            {
                "source_id": "kmc-stub-1",
                "work": "동의보감",
                "retrieval_query": "donguibogam",
                "citation_valid": True,
                "read_only": True,
            }
        ]
    return bundle


def test_prescription_claim_fails_without_classic_refs(tmp_path: Path) -> None:
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(_minimal_bundle(with_refs=False), ensure_ascii=False), encoding="utf-8")
    cp = subprocess.run(
        [sys.executable, str(VALIDATE), "--bundle-json", str(bundle_path), "--policy-json", str(POLICY)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode != 0
    assert "prescription-like" in cp.stderr


def test_patient_med_history_bokyong_in_subjective_passes_without_classic_refs(tmp_path: Path) -> None:
    bundle = _minimal_bundle(with_refs=False)
    bundle["clinical_soap_v1"]["subjective"] = {
        "text": "- 기타: [Hx] 때때로 타이레놀 복용",
    }
    bundle["clinical_soap_v1"]["plan"] = {"text": "처방·침구: 한의사 확정 후 기재"}
    bundle_path = tmp_path / "bundle_hx.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    cp = subprocess.run(
        [sys.executable, str(VALIDATE), "--bundle-json", str(bundle_path), "--policy-json", str(POLICY)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout


def test_hypo_slot_bokyong_echo_passes_without_classic_refs(tmp_path: Path) -> None:
    bundle = _minimal_bundle(with_refs=False)
    bundle["clinical_soap_v1"]["plan"] = {"text": "처방·침구: 한의사 확정 후 기재"}
    bundle["patient_slots"] = [
        {
            "slot_id": "core",
            "title": "Track B",
            "body_markdown": "[HYPO] chart echo: 때때로 타이레놀 복용",
            "included": True,
        }
    ]
    bundle_path = tmp_path / "bundle_hypo_slot.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    cp = subprocess.run(
        [sys.executable, str(VALIDATE), "--bundle-json", str(bundle_path), "--policy-json", str(POLICY)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout


def test_prescription_claim_passes_with_valid_classic_refs(tmp_path: Path) -> None:
    bundle_path = tmp_path / "bundle_ok.json"
    bundle_path.write_text(json.dumps(_minimal_bundle(with_refs=True), ensure_ascii=False), encoding="utf-8")
    cp = subprocess.run(
        [sys.executable, str(VALIDATE), "--bundle-json", str(bundle_path), "--policy-json", str(POLICY)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
