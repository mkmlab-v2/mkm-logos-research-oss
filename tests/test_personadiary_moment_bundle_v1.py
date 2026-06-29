"""PersonaDiary moment bundle v1 — registry sync + lib wire."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_ARTIFACT = ROOT / "docs/final/artifacts/moment_bundle_pair_registry_v1_latest.json"
REGISTRY_PUBLIC = ROOT / "projects/no1kmedi/public/data/moment_bundle_pair_registry_v1.json"
MOMENT_LIB = ROOT / "projects/no1kmedi/src/lib/personadiaryMomentBundleV1.ts"
MOMENT = ROOT / "projects/no1kmedi/src/lib/personadiaryMoment.ts"
CARD_LIB = ROOT / "projects/no1kmedi/src/lib/personadiaryPersonaVisualCardV1.ts"
COMP = ROOT / "projects/no1kmedi/src/components/personadiary/PersonadiaryPersonaVisualCard.tsx"
CHECK = ROOT / "scripts/check_moment_bundle_pair_v1.py"


def test_registry_public_synced() -> None:
    assert REGISTRY_ARTIFACT.is_file()
    assert REGISTRY_PUBLIC.is_file()
    artifact = json.loads(REGISTRY_ARTIFACT.read_text(encoding="utf-8"))
    public = json.loads(REGISTRY_PUBLIC.read_text(encoding="utf-8"))
    assert public["registry_version"] == artifact["registry_version"]
    assert public["schema"] == "moment_bundle_pair_registry_v1"


def test_moment_bundle_lib_wired() -> None:
    lib = MOMENT_LIB.read_text(encoding="utf-8")
    assert "resolveMomentBundle" in lib
    assert "personadiary_moment_bundle_resolved_v1" in lib
    moment = MOMENT.read_text(encoding="utf-8")
    assert "moment_bundle" in moment
    assert "resolveMomentBundle" in moment
    card = CARD_LIB.read_text(encoding="utf-8")
    assert "moment_bundle" in card
    comp = COMP.read_text(encoding="utf-8")
    assert "moment-bundle-v1" in comp
    assert "data-moment-bundle-id" in comp


def test_check_script_exists() -> None:
    assert CHECK.is_file()
    assert "moment_bundle_pair_registry_v1" in CHECK.read_text(encoding="utf-8")
