"""PersonaDiary hyper-local POI catalog v1."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POI = ROOT / "docs/final/artifacts/personadiary_hyper_local_poi_catalog_v1_latest.json"
PUBLIC = ROOT / "projects/no1kmedi/public/data/personadiary_hyper_local_poi_catalog_v1.json"
LIB = ROOT / "projects/no1kmedi/src/lib/personadiaryHyperLocalPoiV1.ts"


def test_poi_catalog_schema_and_gwangmyeong_sample() -> None:
    doc = json.loads(POI.read_text(encoding="utf-8"))
    assert doc["schema"] == "personadiary_hyper_local_poi_catalog_v1"
    entries = doc.get("entries") or []
    assert len(entries) >= 3
    gw = next(e for e in entries if e.get("poi_id") == "gwangmyeong_samgyetang_alley")
    assert "광명" in gw["one_liner_ko"]
    assert "삼계탕" in gw["menu_ko"]


def test_poi_public_mirror_and_ts_loader() -> None:
    assert PUBLIC.is_file()
    assert LIB.is_file()
    assert "pickHyperLocalPoi" in LIB.read_text(encoding="utf-8")
    pub = json.loads(PUBLIC.read_text(encoding="utf-8"))
    assert pub["schema"] == "personadiary_hyper_local_poi_catalog_v1"
