"""P2: hub clinical nav group + canon cite query builder."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "projects/no1kmedi/src/lib/universeHubPluginsV2.ts"
QUERY_TS = ROOT / "projects/no1kmedi/src/lib/km-clinician-canon-cite-query-v1.ts"
CONTRACT = ROOT / "docs/final/artifacts/mkm_universe_hub_shell_contract_v2_draft.json"


def test_hub_clinical_nav_group_in_plugins():
    text = PLUGINS.read_text(encoding="utf-8")
    assert '"clinical"' in text
    assert "national_km_ask" in text
    assert 'navGroup: "clinical"' in text
    assert "임상 · 한의사" in text


def test_hub_sidebar_group_order_includes_clinical():
    sidebar = ROOT / "projects/no1kmedi/src/components/shell/UniverseSidebarV2.tsx"
    text = sidebar.read_text(encoding="utf-8")
    assert '"clinical"' in text
    idx_b2b = text.find('"b2b"')
    idx_clinical = text.find('"clinical"')
    idx_consumer = text.find('"consumer"')
    assert idx_b2b < idx_clinical < idx_consumer


def test_shell_contract_nav_groups_clinical():
    import json

    doc = json.loads(CONTRACT.read_text(encoding="utf-8"))
    hub = doc["shells"]["universe_hub_v2"]
    groups = hub["nav_groups"]
    assert "clinical" in groups
    plugins = hub["sidebar_plugins"]
    ids = [p["id"] for p in plugins]
    assert "national_km_ask" in ids


def test_canon_cite_query_builder_prefers_chief_and_syndrome():
    text = QUERY_TS.read_text(encoding="utf-8")
    assert "buildKmCanonCiteSuggestedQuery" in text
    assert "syndromeHypothesis" in text
