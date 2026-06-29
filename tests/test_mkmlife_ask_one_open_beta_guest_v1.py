"""mkmlife Ask One open-beta guest session + wrangler flag wiring (static gate)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MKMLIFE = ROOT / "projects" / "mkm" / "mkm-life"
NO1KMEDI = ROOT / "projects" / "no1kmedi" / "src"


def test_wrangler_open_beta_var_present() -> None:
    for name in ("wrangler.jsonc", "wrangler.deploy-no-routes.jsonc"):
        text = (MKMLIFE / name).read_text(encoding="utf-8")
        assert "MKM_ASK_ONE_OPEN_BETA" in text
        assert '"1"' in text or "'1'" in text


def test_guest_user_session_helpers() -> None:
    text = (MKMLIFE / "lib" / "mkmlife-user-session-v1.ts").read_text(encoding="utf-8")
    assert "ensureMkmLifeGuestUserId" in text
    assert "MKM_LIFE_GUEST_USER_ID_PREFIX" in text
    assert "guest_" in text


def test_ask_one_open_beta_skips_heavy_validation() -> None:
    page = (MKMLIFE / "app" / "ask-one" / "page.tsx").read_text(encoding="utf-8")
    assert "if (openBetaEnabled)" in page
    assert "ensureMkmLifeGuestUserId" in page


def test_hub_mkmlife_deep_link_helper() -> None:
    text = (NO1KMEDI / "lib" / "universeHubPluginsV2.ts").read_text(encoding="utf-8")
    router = (NO1KMEDI / "lib" / "universeHubIntentRouterV2.ts").read_text(encoding="utf-8")
    assert "buildMkmlifeAskOneHubDeepLink" in text
    assert "buildMkmlifeAskOneHubDeepLink" in router
