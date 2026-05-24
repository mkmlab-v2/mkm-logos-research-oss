from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_status_promote_when_matrix_exists(tmp_path, monkeypatch) -> None:
    spec = importlib.util.spec_from_file_location(
        "build_saving_the_news_phase2_poc_status_v1",
        ROOT / "scripts/build_saving_the_news_phase2_poc_status_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)

    art = tmp_path / "artifacts"
    art.mkdir()
    (art / "saving_the_news_phase2_matrix_view_v1_latest.json").write_text(
        json.dumps(
            {
                "matrix_rows": [
                    {"lens_id": "sasang", "present": True},
                    {"lens_id": "myeongni", "present": True},
                    {"lens_id": "logos", "present": True},
                    {"lens_id": "news", "present": True},
                    {"lens_id": "macro", "present": True},
                ],
                "conflict_resolver": {"conflict": False},
                "final_action": {"action": "WATCH"},
            }
        ),
        encoding="utf-8",
    )
    (art / "saving_the_news_phase1_poc_status_v1_latest.json").write_text(
        json.dumps({"exit_criteria": {"promote_to_phase2": True}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "ART", art)
    monkeypatch.setattr(mod, "MATRIX", art / "saving_the_news_phase2_matrix_view_v1_latest.json")
    monkeypatch.setattr(mod, "PHASE1", art / "saving_the_news_phase1_poc_status_v1_latest.json")
    monkeypatch.setattr(mod, "OUT_JSON", art / "out.json")

    doc = mod.build_status()
    assert doc["exit_criteria"]["promote_to_phase3"] is True
