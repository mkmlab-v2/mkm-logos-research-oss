"""mkmlife Wave 2/3b — cosmic anchor public wire + oracle-sphere integration."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MKMLIFE = ROOT / "projects/mkm/mkm-life"
BATCH_MANIFEST = MKMLIFE / "public/data/logos_cosmic_anchor_batch_v1_manifest_latest.json"
BATCH_PUBLIC = MKMLIFE / "public/data/logos_cosmic_anchor_batch_v1"
LIB = MKMLIFE / "lib/mkmlifeCosmicAnchorV1.ts"
INDEX = MKMLIFE / "lib/mkmlifeCosmicAnchorBatchIndex.generated.ts"
BRIDGE = MKMLIFE / "components/magic-orb/CosmicAnchorFrameBridge.tsx"
API = MKMLIFE / "app/api/v1/design-kernel/cosmic-anchor/route.ts"
ORB = MKMLIFE / "components/magic-orb/MagicOrbExperience.tsx"


def test_mkmlife_cosmic_anchor_public_and_wire() -> None:
    assert BATCH_MANIFEST.is_file()
    manifest = json.loads(BATCH_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["schema"] == "logos_cosmic_anchor_batch_v1_manifest"
    assert manifest["lookup_by_preset_id"]["job_suffering_reason"] == "cosmic_anchor_seed_jhn_12_24"
    assert manifest["anchor_count"] >= 30
    for stem in ("seed", "light", "way", "door"):
        p = BATCH_PUBLIC / f"{stem}.json"
        assert p.is_file(), stem
        doc = json.loads(p.read_text(encoding="utf-8"))
        assert doc["fact_lock"]["forbidden_synthesis"] is True

    assert INDEX.is_file()
    lib = LIB.read_text(encoding="utf-8")
    assert "resolveCosmicAnchorForOrb" in lib
    assert "logos_cosmic_anchor_batch_v1_manifest_latest.json" in lib
    assert "mkmlifeCosmicAnchorBatchIndex.generated" in lib

    bridge = BRIDGE.read_text(encoding="utf-8")
    assert "CosmicAnchorFrameBridge" in bridge
    assert "--orb-survival-min-padding" in bridge

    api = API.read_text(encoding="utf-8")
    assert "mkmlife_cosmic_anchor_api_v1" in api
    assert "lookupCosmicAnchorByVerseRef" in api

    orb = ORB.read_text(encoding="utf-8")
    assert "CosmicAnchorFrameBridge" in orb
    assert "COSMIC-ANCHOR-DRAFT" in orb
    assert "magic-orb-page--cosmic-anchor" in orb
    assert "cosmicVerseRef" in orb
