"""TKM health skin guard."""

from scripts import tkm_health_dialogue_guard_v1 as g


def test_health_disclaimer_ok() -> None:
    assert g.disclaimer_ok(g.DISCLAIMER_TEXT_KO)


def test_health_forbidden_prescription() -> None:
    hits = g.scan_forbidden("이 한약 처방으로 완치됩니다")
    assert "prescription" in hits or "cure_efficacy" in hits or "herbal_rx" in hits
