"""Oracle-sphere localhost live dev helpers (static gate)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MKMLIFE = ROOT / "projects" / "mkm" / "mkm-life"


def test_live_dev_module_exports() -> None:
    text = (MKMLIFE / "lib" / "oracle-sphere-live-dev-v1.ts").read_text(encoding="utf-8")
    assert "readOracleSphereLiveDevEnabled" in text
    assert "ORACLE_SPHERE_LIVE_DEV_POLL_MS" in text


def test_live_dev_panel_wired() -> None:
    exp = (MKMLIFE / "components" / "magic-orb" / "MagicOrbExperience.tsx").read_text(encoding="utf-8")
    assert "OracleSphereLiveDevPanel" in exp
    assert "liveDevMode" in exp
    assert "oracle-sphere-live-dev-panel" in (MKMLIFE / "app" / "globals.css").read_text(encoding="utf-8")


def test_live_dev_runner_scripts_exist() -> None:
    scripts = MKMLIFE / "scripts"
    assert (scripts / "oracle-sphere-live-dev-runner.mjs").is_file()
    assert (scripts / "watch-oracle-sphere-artifacts-dev.mjs").is_file()
    pkg = (MKMLIFE / "package.json").read_text(encoding="utf-8")
    assert "dev:oracle-sphere:live" in pkg


def test_workspace_invoke_script_exists() -> None:
    assert (ROOT / "scripts" / "Invoke-MkmlifeOracleSphereLiveDev_v1.ps1").is_file()
