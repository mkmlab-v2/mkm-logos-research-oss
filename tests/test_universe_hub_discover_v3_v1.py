"""Hub discover v3 — dark tokens, sidebar collapse, inspector artifacts (static gate)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NO1KMEDI = ROOT / "projects" / "no1kmedi" / "src"


def test_discover_v3_css_tokens_present() -> None:
    css = (NO1KMEDI / "app" / "globals.css").read_text(encoding="utf-8")
    assert "universe-hub-page--discover-v3" in css
    assert "--hub-bg: #191919" in css
    assert "--hub-surface: #202020" in css
    assert "--hub-border: #2a2a2a" in css


def test_sidebar_collapse_hook_wired() -> None:
    shell = (NO1KMEDI / "components" / "shell" / "UnifiedUniverseShellV2.tsx").read_text(
        encoding="utf-8"
    )
    sidebar = (NO1KMEDI / "components" / "shell" / "UniverseSidebarV2.tsx").read_text(
        encoding="utf-8"
    )
    hook = (NO1KMEDI / "hooks" / "useHubSidebarCollapsedV1.ts").read_text(encoding="utf-8")
    assert "useHubSidebarCollapsedV1" in hook
    assert "useHubSidebarCollapsedV1" in shell
    assert "universe-hub-sidebar-collapse" in sidebar
    assert "onToggleCollapse" in sidebar


def test_inspector_discover_logos_stub_copy() -> None:
    inspector = (NO1KMEDI / "components" / "shell" / "HubEvidenceInspectorV3.tsx").read_text(
        encoding="utf-8"
    )
    artifacts = (NO1KMEDI / "lib" / "universeHubInspectorArtifactsV1.ts").read_text(encoding="utf-8")
    assert "Logos Observatory" in inspector
    assert "[HYPO]" in inspector
    assert "universeHubInspectorArtifactsV1" in inspector
    assert "HUB_INSPECTOR_ARTIFACTS_V1" in artifacts
    assert "universe-hub-artifact-path" in inspector


def test_mkmlife_embed_dev_pair_auto_enable_wired() -> None:
    embed = (NO1KMEDI / "lib" / "universeHubMkmlifeEmbedV2.ts").read_text(encoding="utf-8")
    assert "isLocalMkmlifeDevPairOrigin" in embed
    assert "NODE_ENV" in embed


def test_mkmlife_hub_embed_tokens_in_globals() -> None:
    css = (ROOT / "projects" / "mkm" / "mkm-life" / "app" / "globals.css").read_text(encoding="utf-8")
    assert "data-hub-embed='1'" in css
    assert "--hub-bg: #191919" in css
