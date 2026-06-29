"""mkmlife ask-one: L0 pediatric panel collapsed for hub embed + general default."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_l0_clinical_panel_uses_details_collapsible():
    path = ROOT / "projects/mkm/mkm-life/components/ask-one/L0ClinicalContextPanel.tsx"
    text = path.read_text(encoding="utf-8")
    assert "askone-l0-clinical-details" in text
    assert "isJemaHubEmbed" in text
    assert "보호자·소아 성장·대사 (해당 시 펼치기)" in text


def test_jema_hub_embed_helper_exists():
    path = ROOT / "projects/mkm/mkm-life/lib/jema-hub-embed-v1.ts"
    text = path.read_text(encoding="utf-8")
    assert "isJemaHubEmbed" in text
    assert "jema_hub_v2" in text


def test_l0_active_helper_in_lib():
    path = ROOT / "projects/mkm/mkm-life/lib/l0-clinical-context-v1.ts"
    text = path.read_text(encoding="utf-8")
    assert "isL0ClinicalContextActive" in text
