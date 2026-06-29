"""l0_red_flag_router_v1 — TKM L0 router smoke."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.l0_red_flag_router_v1 import (
    collect_l0_state_from_bundle,
    collect_l0_state_from_sequence,
    format_patient_markdown_block,
    keyword_hits_from_text,
    load_template,
    merge_l0_states,
)
from scripts.patch_patient_care_bundle_encounter_sequence_ref_v1 import patch_bundle
from scripts.render_patient_care_bundle_markdown_v1 import render_bundle_markdown

ROOT = Path(__file__).resolve().parents[1]
SEQ = ROOT / "tests/fixtures/encounter_sequence_v1.example.json"
MINIMAL = ROOT / "docs/final/schemas/patient_care_bundle_v1.minimal.example.json"


def test_template_loads() -> None:
    tpl = load_template()
    assert tpl.get("template_id") == "l0_red_flag_escalation_ko_v1"


def test_sequence_triggers_l0() -> None:
    seq = json.loads(SEQ.read_text(encoding="utf-8-sig"))
    state = collect_l0_state_from_sequence(seq)
    assert state.get("triggered") is True
    block = format_patient_markdown_block(state)
    assert "L0 안전 알림" in block


def test_bundle_render_l0_top() -> None:
    bundle = json.loads(MINIMAL.read_text(encoding="utf-8-sig"))
    seq = json.loads(SEQ.read_text(encoding="utf-8-sig"))
    patched = patch_bundle(
        bundle,
        encounter_ref="ENC-DEMO",
        encounter_sequence_id=seq["encounter"]["sequence_id"],
        encounter_sequence_ledger_ref="data/clinic/encounter_sequence_v1.sample.jsonl",
    )
    md = render_bundle_markdown(patched, encounter_sequence=seq)
    barrier_idx = md.find("Track B")
    l0_idx = md.find("L0 안전 알림")
    soap_idx = md.find("## SOAP")
    assert l0_idx > barrier_idx > 0
    assert l0_idx < soap_idx


def test_keyword_scan() -> None:
    tpl = load_template()
    hits = keyword_hits_from_text("severe_abdominal_pain reported", tpl)
    assert "severe_abdominal_pain" in hits


def test_postpartum_ko_keyword_scan() -> None:
    tpl = load_template()
    hits = keyword_hits_from_text("산후 3일째 고열 39도 지속", tpl)
    assert "고열" in hits
    assert "39도" in hits
    hits_bleed = keyword_hits_from_text("대량 출혈이 있어 응급실 방문", tpl)
    assert "대량 출혈" in hits_bleed


def test_bundle_l0_scan_negative() -> None:
    bundle = json.loads(MINIMAL.read_text(encoding="utf-8-sig"))
    state = collect_l0_state_from_bundle(bundle)
    assert state.get("triggered") is False


def test_bundle_l0_scan_positive_postpartum() -> None:
    bundle = json.loads(MINIMAL.read_text(encoding="utf-8-sig"))
    soap = bundle.setdefault("clinical_soap_v1", {})
    soap["subjective"] = {"text": "산후 5일째 고열 39도 지속, 대량 출혈 없음"}
    state = collect_l0_state_from_bundle(bundle)
    assert state.get("triggered") is True
    hits = state.get("keyword_hits") or []
    assert "고열" in hits
    assert "39도" in hits


def test_merge_l0_states_or() -> None:
    seq_state = {"triggered": False, "keyword_hits": [], "escalation_copy_id": "l0_red_flag_escalation_ko_v1"}
    bundle_state = {"triggered": True, "keyword_hits": ["고열"], "escalation_copy_id": "l0_red_flag_escalation_ko_v1"}
    merged = merge_l0_states(seq_state, bundle_state)
    assert merged.get("triggered") is True
    assert "고열" in (merged.get("keyword_hits") or [])
