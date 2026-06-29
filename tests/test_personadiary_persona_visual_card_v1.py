"""PersonaDiary persona visual card v1 preview."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "projects/no1kmedi/src/lib/personadiaryPersonaVisualCardV1.ts"
KERNEL_LIB = ROOT / "projects/no1kmedi/src/lib/personadiaryDesignKernelV1.ts"
COMP = ROOT / "projects/no1kmedi/src/components/personadiary/PersonadiaryPersonaVisualCard.tsx"
HOME = ROOT / "projects/no1kmedi/src/components/personadiary/PersonadiaryPremiumHome.tsx"


def test_persona_visual_card_files_wired() -> None:
    assert LIB.is_file()
    assert KERNEL_LIB.is_file()
    assert COMP.is_file()
    assert "buildPersonaVisualCardView" in LIB.read_text(encoding="utf-8")
    assert "acode_public" in LIB.read_text(encoding="utf-8")
    assert "pd-persona-visual-acode" in COMP.read_text(encoding="utf-8")
    assert "pd-persona-visual-card" in COMP.read_text(encoding="utf-8")
    assert "design-kernel-v1" in COMP.read_text(encoding="utf-8")
    home = HOME.read_text(encoding="utf-8")
    assert "PersonadiaryPersonaVisualCard" in home
