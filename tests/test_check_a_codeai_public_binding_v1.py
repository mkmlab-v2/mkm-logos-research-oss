from __future__ import annotations

from scripts import check_a_codeai_public_binding_v1 as mod


def test_pilot_narrative_ok():
    en = "app.jema-ai.com/enterprise/apply 628-86-01742 compression open bench"
    ko = "app.jema-ai.com/enterprise/apply 628-86-01742 압축 오픈벤치"
    ok, details = mod._check_pilot_narrative(pilot_en=en, pilot_ko=ko)
    assert ok is True
    assert details["forbidden_hits"] == []


def test_pilot_narrative_rejects_legacy_copy():
    en = "treasury risk monitoring app.jema-ai.com/enterprise/apply 628-86-01742"
    ko = "app.jema-ai.com/enterprise/apply 628-86-01742"
    ok, details = mod._check_pilot_narrative(pilot_en=en, pilot_ko=ko)
    assert ok is False
    assert "treasury" in details["forbidden_hits"]


def test_legal_page_ok():
    en = "Moksori Network 628-86-01742 jema-ai.com/privacy SEND_GATE HOLD"
    ko = "목소리네트워크 628-86-01742 jema-ai.com/privacy HOLD"
    ok, _ = mod._check_legal_page(legal_en=en, legal_ko=ko)
    assert ok is True
