"""PersonaDiary Logos sidebar local diary rerank parity."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "scripts/build_personadiary_logos_sidebar_smoke_v1.py"


def _load_builder():
    spec = importlib.util.spec_from_file_location("pd_sidebar_build", MOD)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_local_diary_text_changes_concept_bridge_rank() -> None:
    mod = _load_builder()
    philosophy = mod._read_json(ROOT / "docs/final/artifacts/philosophy_lane_rag_pilot_v1_latest.json")
    graphrag = mod._read_json(ROOT / "docs/final/artifacts/graphrag_pilot_router_latest.json")
    registry = mod._read_json(ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json")
    pools = mod._build_candidate_pools(philosophy, graphrag, registry)

    rest_text = "쉼도 의도적으로 설계한다"
    chip_text = "반도체 공급망과 정제 유리 은유를 메모한다"

    rest_bridge = mod._concept_bridge_hit(registry, rest_text)
    chip_bridge = mod._concept_bridge_hit(registry, chip_text)

    assert rest_bridge is not None
    assert chip_bridge is not None
    assert rest_bridge.get("concept_id") == "concept:mercy_after_turmoil"
    assert chip_bridge.get("concept_id") == "concept:semiconductor"
    assert rest_bridge.get("score") != chip_bridge.get("score")
    assert pools["logos_ann_lite"]
