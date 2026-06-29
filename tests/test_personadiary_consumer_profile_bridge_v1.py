"""PersonaDiary consumer profile bridge (TS module contract)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "projects/no1kmedi/src/lib/personadiaryConsumerProfileV1.ts"
STORE = ROOT / "projects/no1kmedi/src/lib/personadiaryMobileOpsStore.ts"


def test_consumer_profile_module_exports() -> None:
    text = LIB.read_text(encoding="utf-8")
    assert "mkm_consumer_profile_v1" in text
    assert "getOrCreatePersonadiaryUserId" in text
    assert "syncConsumerProfileFromOps" in text
    assert "hydrateOpsFromCachedConsumerProfile" in text
    assert "no mkmlife API" in text


def test_mobile_ops_store_wires_consumer_bridge() -> None:
    text = STORE.read_text(encoding="utf-8")
    assert "hydrateOpsFromCachedConsumerProfile" in text
    assert "syncConsumerProfileFromOps" in text
