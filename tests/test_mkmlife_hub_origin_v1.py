"""Hub → mkmlife local dev origin resolver (static gate)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NO1KMEDI_LIB = ROOT / "projects" / "no1kmedi" / "src" / "lib"


def test_mkmlife_hub_origin_module_exists() -> None:
    path = NO1KMEDI_LIB / "mkmlife-hub-origin-v1.ts"
    text = path.read_text(encoding="utf-8")
    assert "NEXT_PUBLIC_MKMLIFE_ORIGIN" in text
    assert "resolveMkmlifeAskOneUrl" in text
    assert "buildUniverseHubMkmlifeDeepLinks" in text


def test_universe_hub_plugins_use_origin_resolver() -> None:
    plugins = (NO1KMEDI_LIB / "universeHubPluginsV2.ts").read_text(encoding="utf-8")
    assert "buildUniverseHubMkmlifeDeepLinks" in plugins
    assert 'mkmlifeHome: MKMLIFE' not in plugins


def test_env_example_documents_local_pair() -> None:
    example = (ROOT / "projects" / "no1kmedi" / ".env.example").read_text(encoding="utf-8")
    assert "NEXT_PUBLIC_MKMLIFE_ORIGIN=http://localhost:3105" in example
