"""Hub showroom CTA (public-copy.json) aligns with minimal board entry URL."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_COPY = ROOT / "projects" / "no1kmedi" / "marketing-site" / "public-copy.json"
BOARD_HTML = (
    ROOT
    / "projects"
    / "bitcoin-trading"
    / "ops"
    / "windows-rehearsal"
    / "jemaai-cloud-mvp"
    / "public_showroom_board_minimal.html"
)


def test_showroom_hub_href_in_board_html() -> None:
    data = json.loads(PUBLIC_COPY.read_text(encoding="utf-8"))
    href = data["hub_links"]["showroom_jemaai"]["href"]
    sublabel = data["hub_links"]["showroom_jemaai"]["sublabel"]
    html = BOARD_HTML.read_text(encoding="utf-8")
    assert href.startswith("https://api.jemaai.cloud/")
    assert href.endswith("public_showroom_board_minimal.html")
    assert "jemaai.cloud" in html
    assert "미니멀 정적 보드" in sublabel
    assert "투자 권유" in sublabel and "주문" in sublabel
