from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def test_spend_gate_blocks_veo_api_by_default():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/cinematic/check_cinematic_veo_spend_gate_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    out = ART / "cinematic_veo_spend_gate_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    decision = doc.get("decision") or {}
    assert decision.get("allow_veo_api") is False


def test_injection_manifest_builder_from_disk_reports():
    economy = ART / "auditable_cinematic_poc_economy_latest.json"
    hybrid = ART / "auditable_cinematic_poc_hybrid_latest.json"
    if not economy.is_file():
        pytest.skip("economy report missing — run free bundle first")
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/cinematic/build_cinematic_injection_manifest_v1.py"),
            "--economy-report",
            str(economy),
            "--hybrid-report",
            str(hybrid),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    manifest = ART / "cinematic_injection_manifest_v1_latest.json"
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    assert doc["schema"] == "cinematic_injection_manifest_v1"
    assert doc["economy"]["scenario_aligned"] is True
    if hybrid.is_file():
        assert doc["hybrid"]["scenario_aligned"] is False
        assert "disclaimer" in doc["hybrid"]


def test_hero_rubric_check_no_veo_api():
    economy = ART / "auditable_cinematic_poc_economy_latest.json"
    if not economy.is_file():
        pytest.skip("economy report missing — run free bundle first")
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/cinematic/check_cinematic_hero_rubric_v1.py"),
            "--economy-report",
            str(economy),
            "--hybrid-report",
            str(ART / "auditable_cinematic_poc_hybrid_latest.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads((ART / "cinematic_hero_rubric_check_v1_latest.json").read_text(encoding="utf-8"))
    assert doc.get("ok") is True
    assert (doc.get("economy") or {}).get("ok") is True


def test_kocca_partner_brief_from_disk():
    bundle = ART / "auditable_cinematic_free_bundle_v1_latest.json"
    if not bundle.is_file():
        pytest.skip("bundle missing — run free bundle first")
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/cinematic/build_cinematic_kocca_partner_brief_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads((ART / "cinematic_kocca_partner_brief_v1_latest.json").read_text(encoding="utf-8"))
    assert doc["schema"] == "cinematic_kocca_partner_brief_v1"
    assert doc["positioning"]["solo_application_fit"] == "low"
    assert len(doc.get("vp_scene_list") or []) >= 6
    md = ART / "cinematic_kocca_partner_brief_v1_latest.md"
    assert md.is_file() and "KOCCA" in md.read_text(encoding="utf-8")


def test_auditable_audio_mix_report():
    mix = ART / "auditable_cinematic_audio_mix_v1_latest.json"
    if not mix.is_file():
        pytest.skip("audio mix report missing — run free bundle or audio mix script")
    doc = json.loads(mix.read_text(encoding="utf-8"))
    assert doc["schema"] == "auditable_cinematic_audio_mix_v1"
    assert doc.get("cost_usd") == 0
    stack = doc.get("audio_stack") or {}
    assert stack.get("promo_pack") is True
    assert stack.get("lens_music_gate") is False
    for row in doc.get("variants") or []:
        assert row.get("ok") is True
        assert Path(row["deliverable_mp4"]).is_file()
