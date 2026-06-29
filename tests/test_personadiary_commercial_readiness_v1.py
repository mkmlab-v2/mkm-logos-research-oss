"""PersonaDiary commercial readiness gate."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NO1KMEDI = ROOT / "projects/no1kmedi"


def test_commercial_home_wiring() -> None:
    home = (NO1KMEDI / "src/components/personadiary/PersonadiaryPremiumHome.tsx").read_text(
        encoding="utf-8"
    )
    assert "pd-commercial-home-v1" in home
    assert "PersonadiaryPlusTeaser" in home
    assert "pd-commercial-moment-section" in home


def test_moment_quota_module() -> None:
    lib = (NO1KMEDI / "src/lib/personadiaryMomentQuotaV1.ts").read_text(encoding="utf-8")
    assert "MOMENT_FREE_DAILY_LIMIT = 3" in lib
    assert "consumeMomentQuota" in lib


def test_commercial_readiness_runner_exists() -> None:
    script = ROOT / "scripts/run_personadiary_commercial_readiness_v1.py"
    invoke = ROOT / "scripts/Invoke-PersonadiaryCommercialReadiness_v1.ps1"
    assert script.is_file()
    assert invoke.is_file()
    assert "personadiary_commercial_readiness_v1" in script.read_text(encoding="utf-8")


def test_live_ops_smoke_has_commercial_markers() -> None:
    smoke = (ROOT / "scripts/run_personadiary_live_ops_smoke_v1.py").read_text(encoding="utf-8")
    assert "COMMERCIAL_HTML_MARKERS" in smoke
    assert "commercial_home_html" in smoke
