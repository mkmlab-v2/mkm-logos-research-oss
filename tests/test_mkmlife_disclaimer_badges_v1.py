"""mkmlife §10.1 disclaimer badge SSOT wiring."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MKMLIFE = ROOT / "projects" / "mkm" / "mkm-life"
BADGES = MKMLIFE / "lib" / "mkmlife-disclaimer-badges-v1.ts"
PANEL = MKMLIFE / "components" / "magic-orb" / "DisclaimerPanel.tsx"
HOME = MKMLIFE / "app" / "page.tsx"
PRICING = MKMLIFE / "app" / "pricing" / "page.tsx"
ASK_ONE = MKMLIFE / "app" / "ask-one" / "page.tsx"
MY_REPORTS = MKMLIFE / "app" / "my-reports" / "page.tsx"


def test_mkmlife_disclaimer_badge_ssot_present() -> None:
    text = BADGES.read_text(encoding="utf-8")
    assert "NON-MEDICAL" in text
    assert "NON-DETERMINISTIC" in text
    assert "FINANCIAL-RISK" in text
    assert "진단·처방·치료를 대체하지 않습니다" in text
    assert "MKMLIFE_HOME_BADGE_IDS" in text


def test_disclaimer_panel_imports_ssot() -> None:
    panel = PANEL.read_text(encoding="utf-8")
    assert "mkmlife-disclaimer-badges-v1" in panel
    assert "MKMLIFE_DISCLAIMER_BADGE_COPY" in panel


def test_home_and_pricing_wire_disclaimer_panel() -> None:
    home = HOME.read_text(encoding="utf-8")
    pricing = PRICING.read_text(encoding="utf-8")
    ask_one = ASK_ONE.read_text(encoding="utf-8")
    my_reports = MY_REPORTS.read_text(encoding="utf-8")
    assert "DisclaimerPanel" in home
    assert "MKMLIFE_HOME_BADGE_IDS" in home
    assert "DisclaimerPanel" in pricing
    assert "DisclaimerPanel" in ask_one
    assert "MKMLIFE_HOME_BADGE_IDS" in ask_one
    assert "DisclaimerPanel" in my_reports
    assert "MKMLIFE_HOME_BADGE_IDS" in my_reports
    assert "ChatGPT" not in home
