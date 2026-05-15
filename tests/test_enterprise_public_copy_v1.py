"""Enterprise hub copy (public-copy.json) — category-first, no LG trophy language."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_COPY = ROOT / "projects" / "no1kmedi" / "marketing-site" / "public-copy.json"


def test_enterprise_block_present_and_links() -> None:
    data = json.loads(PUBLIC_COPY.read_text(encoding="utf-8"))
    ent = data["enterprise"]
    assert data["links"]["enterprise"] == "/enterprise"
    assert "운영 게이트" in ent["hero"]["title"]
    assert len(ent["pillars"]["cards"]) >= 3
    showroom = data["hub_links"]["showroom_jemaai"]["href"]
    assert showroom.startswith("https://api.jemaai.cloud/")
    hero = ent["hero"]["title"] + ent["hero"]["subtitle"]
    for banned in ("LG전자", "LG ", "합격", "수상"):
        assert banned not in hero
    assert "실시간 무지연" not in ent["hero"]["subtitle"]
    assert "수익 보장" not in ent["hero"]["subtitle"]
    assert ent["contact"]["email"] == "support@mkmlife.com"
    assert "gmbaekje@naver.com" not in json.dumps(ent)
    assert "광명백제" not in json.dumps(ent)
    foot = ent["footer"]
    assert "목소리네트워크" in foot["legal_entity"]
    assert "sub_brand_note" not in foot
    site_foot = data["footer"]
    assert "목소리네트워크" in site_foot["company_line"]
    assert site_foot["email"] == "support@mkmlife.com"
    assert "광명백제" not in json.dumps(site_foot)
