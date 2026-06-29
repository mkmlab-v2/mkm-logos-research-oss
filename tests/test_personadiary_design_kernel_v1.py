"""PersonaDiary design kernel v1 wire — charter + public data + lib."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KERNEL_ARTIFACT = ROOT / "docs/final/artifacts/sasang_design_primitive_kernel_v1_latest.json"
KERNEL_PUBLIC = ROOT / "projects/no1kmedi/public/data/sasang_design_primitive_kernel_v1.json"
EMOTION_PUBLIC = ROOT / "projects/no1kmedi/public/data/sasang_emotion_mapping_v1.json"
LIB = ROOT / "projects/no1kmedi/src/lib/personadiaryDesignKernelV1.ts"
CARD_LIB = ROOT / "projects/no1kmedi/src/lib/personadiaryPersonaVisualCardV1.ts"
COMP = ROOT / "projects/no1kmedi/src/components/personadiary/PersonadiaryPersonaVisualCard.tsx"


def test_design_kernel_public_data_synced() -> None:
    assert KERNEL_ARTIFACT.is_file()
    assert KERNEL_PUBLIC.is_file()
    artifact = json.loads(KERNEL_ARTIFACT.read_text(encoding="utf-8"))
    public = json.loads(KERNEL_PUBLIC.read_text(encoding="utf-8"))
    assert public["kernel_version"] == artifact["kernel_version"]
    assert EMOTION_PUBLIC.is_file()


def test_design_kernel_lib_exports_and_card_wired() -> None:
    lib = LIB.read_text(encoding="utf-8")
    assert "resolveDesignKernelForPersonadiary" in lib
    assert "applyDesignKernelToPalette" in lib
    card = CARD_LIB.read_text(encoding="utf-8")
    assert "resolveDesignKernelForPersonadiary" in card
    assert "design_kernel" in card
    comp = COMP.read_text(encoding="utf-8")
    assert "design-kernel-v1" in comp
    assert "data-design-kernel-version" in comp
    assert "data-pathology-state" in comp


def test_personadiary_product_depth_in_kernel() -> None:
    doc = json.loads(KERNEL_PUBLIC.read_text(encoding="utf-8"))
    pd = doc["product_depth"]["personadiary.com"]
    assert "pathology" in pd["primitives"]
    assert "valence" in pd["primitives"]
    assert pd["extensions"] == []
