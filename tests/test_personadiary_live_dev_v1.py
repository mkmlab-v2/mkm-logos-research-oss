"""PersonaDiary Design Lane — local live dev helpers."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NO1KMEDI = ROOT / "projects" / "no1kmedi"


def test_personadiary_live_dev_scripts_exist() -> None:
    scripts = NO1KMEDI / "scripts"
    pkg = (NO1KMEDI / "package.json").read_text(encoding="utf-8")
    assert (scripts / "smoke-personadiary-dev.mjs").is_file()
    assert (scripts / "watch-personadiary-dev.mjs").is_file()
    assert (scripts / "personadiary-live-dev-runner.mjs").is_file()
    assert (scripts / "watch-personadiary-artifacts-dev.mjs").is_file()
    assert "dev:personadiary:live" in pkg


def test_personadiary_smoke_contract_markers() -> None:
    smoke = (NO1KMEDI / "scripts" / "smoke-personadiary-dev.mjs").read_text(encoding="utf-8")
    assert "찰나의 나" in smoke
    assert "personadiary_daily_response_package_v1" in smoke
    assert "/api/personadiary/moment" in smoke


def test_personadiary_watch_roots() -> None:
    watch = (NO1KMEDI / "scripts" / "watch-personadiary-dev.mjs").read_text(encoding="utf-8")
    assert "components/personadiary" in watch
    assert "smoke-personadiary-dev.mjs" in watch


def test_personadiary_invoke_script() -> None:
    invoke = (ROOT / "scripts" / "Invoke-PersonadiaryDesignLiveDev_v1.ps1").read_text(encoding="utf-8")
    assert "dev:personadiary:live" in invoke
    assert "/personadiary" in invoke
    assert "3010" in invoke
