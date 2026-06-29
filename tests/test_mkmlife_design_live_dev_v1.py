"""MKMLIFE Design Lane — home + oracle local live dev helpers."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MKMLIFE = ROOT / "projects" / "mkm" / "mkm-life"


def test_home_live_dev_scripts_exist() -> None:
    scripts = MKMLIFE / "scripts"
    pkg = (MKMLIFE / "package.json").read_text(encoding="utf-8")
    assert (scripts / "smoke-mkmlife-home-dev.mjs").is_file()
    assert (scripts / "watch-mkmlife-home-dev.mjs").is_file()
    assert (scripts / "mkmlife-design-live-dev-runner.mjs").is_file()
    assert "dev:mkmlife:home:live" in pkg
    assert "dev:mkmlife:design:live" in pkg


def test_home_smoke_contract_markers() -> None:
    smoke = (MKMLIFE / "scripts" / "smoke-mkmlife-home-dev.mjs").read_text(encoding="utf-8")
    assert "landing-life-portal" in smoke
    assert "mkmlife_news_observation_deck_v1" in smoke
    assert "관측 구" in smoke


def test_home_watch_roots() -> None:
    watch = (MKMLIFE / "scripts" / "watch-mkmlife-home-dev.mjs").read_text(encoding="utf-8")
    assert "components/home" in watch
    assert "app/page.tsx" in watch
    assert "smoke-mkmlife-home-dev.mjs" in watch


def test_design_invoke_script_lanes() -> None:
    invoke = (ROOT / "scripts" / "Invoke-MkmlifeDesignLiveDev_v1.ps1").read_text(encoding="utf-8")
    assert "ValidateSet('home', 'oracle', 'all')" in invoke
    assert "dev:mkmlife:design:live" in invoke
    assert "dev:portal:restart" in invoke


def test_middleware_portal_home_bypass() -> None:
    mw = (MKMLIFE / "middleware.ts").read_text(encoding="utf-8")
    assert "MKM_MKMLIFE_DESIGN_LIVE_DEV" in mw
    assert (MKMLIFE / "scripts" / "dev-design-portal.mjs").is_file()
    assert (MKMLIFE / "scripts" / "mkmlife-dev-port.mjs").is_file()
    assert (MKMLIFE / "scripts" / "mkmlife-dev-port-lib.mjs").is_file()
    pkg = (MKMLIFE / "package.json").read_text(encoding="utf-8")
    assert "dev:portal:restart" in pkg
    assert "dev:portal:status" in pkg


def test_dev_port_lib_contract() -> None:
    lib = (MKMLIFE / "scripts" / "mkmlife-dev-port-lib.mjs").read_text(encoding="utf-8")
    assert "probePortalHealth" in lib
    assert "ensureMkmlifeDevPort" in lib
    assert "life-portal" in lib
    cli = (MKMLIFE / "scripts" / "mkmlife-dev-port.mjs").read_text(encoding="utf-8")
    assert "mkmlife_dev_port_restart_v1" in cli
    portal = (MKMLIFE / "scripts" / "dev-design-portal.mjs").read_text(encoding="utf-8")
    assert "ensureMkmlifeDevPort" in portal
    assert "reuse" in portal


def test_oracle_invoke_delegates_to_design() -> None:
    legacy = (ROOT / "scripts" / "Invoke-MkmlifeOracleSphereLiveDev_v1.ps1").read_text(encoding="utf-8")
    assert "Invoke-MkmlifeDesignLiveDev_v1.ps1" in legacy
    assert "-Lane oracle" in legacy
