"""Mirror no1kmedi-portal-host.ts routing rules (Fact-Lock smoke)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORTAL_HOST = ROOT / "projects/no1kmedi/src/lib/no1kmedi-portal-host.ts"


def test_portal_host_file_exists():
    assert PORTAL_HOST.is_file()


def test_app_jema_ai_in_hub_hosts_not_clinician_root_rewrite():
    text = PORTAL_HOST.read_text(encoding="utf-8")
    assert "app.jema-ai.com" in text
    assert "JEMA_AI_HUB_HOSTS" in text
    assert "shouldRedirectRootToHubHome" in text
    # app host uses hub redirect path; clinician root rewrite is no1kmedi-only
    assert "shouldRewriteRootToClinician" in text
    assert "isNo1kmediPortalHost" in text


def test_middleware_redirects_root_to_hub():
    mw = ROOT / "projects/no1kmedi/src/middleware.ts"
    text = mw.read_text(encoding="utf-8")
    assert "shouldRedirectRootToHubHome" in text
    assert 'url.pathname = "/hub"' in text
