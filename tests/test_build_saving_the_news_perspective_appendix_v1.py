from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_entity_tokens_from_headline() -> None:
    mod = _load("appendix", "scripts/build_saving_the_news_perspective_appendix_v1.py")
    tokens = mod._entity_tokens("Fed holds rates after inflation shock in Korea market")
    assert "fed" in tokens or "inflation" in tokens
    assert "the" not in tokens


def test_build_appendix_contract_minimal(tmp_path: Path, monkeypatch) -> None:
    mod = _load("appendix", "scripts/build_saving_the_news_perspective_appendix_v1.py")
    art = tmp_path / "artifacts"
    art.mkdir()
    matrix = {
        "headline_anchor": {"headline": "위기 속 언약의 안정", "timestamp_utc": "2026-05-24T00:00:00Z"},
    }
    matrix_path = art / "matrix.json"
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
    registry = {"entries": []}
    (art / "registry.json").write_text(json.dumps(registry), encoding="utf-8")
    monkeypatch.setattr(mod, "ART", art)

    doc = mod.build_appendix(
        matrix_path=matrix_path,
        pre_news_path=art / "missing_pre_news.json",
        flywheel_path=art / "flywheel.json",
        registry_path=art / "registry.json",
        lemma_path=art / "lemma.jsonl",
        seed_chain_path=art / "seed.json",
        router_out=art / "router.json",
        top_bridges=1,
    )
    assert doc["schema"] == "saving_the_news_perspective_appendix_v1"
    assert doc["ready_for_external_send"] is False
    assert doc["layer"] == "B"
    assert len(doc["perspective_slots"]) == 3
    assert doc["coordinator_brief_ko"].startswith("[HYPO]")


def test_flywheel_snapshot_axes() -> None:
    mod = _load("flywheel", "scripts/build_saving_the_news_flywheel_as_snapshot_v1.py")
    doc = mod.build_snapshot()
    assert doc["schema"] == "saving_the_news_flywheel_as_snapshot_v1"
    assert doc["flywheel_stage"] == "4_as_transparency"
    assert isinstance(doc.get("axes"), list)
