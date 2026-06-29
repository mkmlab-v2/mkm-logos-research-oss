"""Patient clinical SSOT resolver gate."""

from __future__ import annotations

import json

from scripts.resolve_patient_clinical_ssot_v1 import resolve

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent


def test_resolve_kim_areum_by_display() -> None:
    code, result = resolve(ROOT, display="김아름")
    assert code == 0
    assert result["slug"] == "kim_areum"
    assert result["ref_token"] == "KIM-AREUM-2026-001"
    assert result["answer_gate"] == "allow"
    assert "kim_areum_intake_ssot_pointer" in result["pointer"]


def test_resolve_lee_bomi_by_slug() -> None:
    code, result = resolve(ROOT, slug="lee_bomi")
    assert code == 0
    assert result["display_label"] == "이보미"
    assert result["ref_token"] == "LEE-BOMI-2026-001"


def test_resolve_not_found() -> None:
    code, result = resolve(ROOT, display="존재하지않는환자")
    assert code == 1
    assert result["answer_gate"] == "deny_not_found"


def test_risk_keywords_ambiguous_without_name() -> None:
    code, result = resolve(ROOT, risk_keywords=["산후", "단삼", "소염"])
    assert code == 2
    assert result["answer_gate"] == "deny_ambiguous"
    slugs = {c["slug"] for c in result["ambiguous"]["candidates"]}
    assert slugs == {"lee_bomi", "kim_areum"}


def test_kim_areum_saved_complete_no_reask_birth() -> None:
    code, result = resolve(ROOT, slug="kim_areum")
    assert code == 0
    mem = result.get("track_b_memory") or {}
    assert mem.get("saved_complete") is True
    assert "saved_long_term_memory" in str(mem.get("intake_status") or "")


def test_cli_main_kim_areum() -> None:
    import subprocess

    proc = subprocess.run(
        ["py", "scripts/resolve_patient_clinical_ssot_v1.py", "--slug", "kim_areum", "--compact"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["slug"] == "kim_areum"
