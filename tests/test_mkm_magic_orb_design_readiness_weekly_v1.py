"""Offline: Magic Orb design readiness weekly task wiring."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_weekly_routine_scripts_exist():
    for name in (
        "Invoke-MkmMagicOrbDesignReadinessWeeklyRoutine_v1.ps1",
        "Register-MkmMagicOrbDesignReadinessWeeklyTask_v1.ps1",
        "Verify-MkmMagicOrbDesignReadinessWeeklyScheduledTask_v1.ps1",
    ):
        assert (ROOT / "scripts" / name).is_file(), name


def test_scheduler_tier4_lists_design_readiness_weekly():
    stack = ROOT / "docs/final/artifacts/mkm_scheduler_solo_core_stack_v1.json"
    text = stack.read_text(encoding="utf-8")
    assert "MKM_MagicOrb_DesignReadiness_Weekly" in text


def test_consumer_mode_tabs_component_exists():
    path = ROOT / "projects/mkm/mkm-life/components/magic-orb/OrbConsumerModeTabs.tsx"
    text = path.read_text(encoding="utf-8")
    assert "magic-orb-consumer-mode-tabs" in text
    assert "ConsumerOrbMode" in text


def test_consumer_reveal_dock_component_exists():
    path = ROOT / "projects/mkm/mkm-life/components/magic-orb/OrbConsumerRevealDock.tsx"
    text = path.read_text(encoding="utf-8")
    assert "magic-orb-consumer-reveal-dock" in text
