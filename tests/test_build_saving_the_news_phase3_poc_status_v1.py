from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_status_complete_when_gating_combined(tmp_path, monkeypatch) -> None:
    spec = importlib.util.spec_from_file_location(
        "build_saving_the_news_phase3_poc_status_v1",
        ROOT / "scripts/build_saving_the_news_phase3_poc_status_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)

    art = tmp_path
    (art / "saving_the_news_phase3_truth_gating_v1_latest.json").write_text(
        json.dumps({"combined_all_passed": True, "outcome_class": "pass_candidate", "publish_signoff": {"cms_publish_allowed": False}, "explicit_not_implemented": []}),
        encoding="utf-8",
    )
    (art / "saving_the_news_phase2_poc_status_v1_latest.json").write_text(
        json.dumps({"exit_criteria": {"promote_to_phase3": True}}),
        encoding="utf-8",
    )
    (art / "saving_the_news_public_event_ingest_stub_v1.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(mod, "ART", art)
    monkeypatch.setattr(mod, "GATING", art / "saving_the_news_phase3_truth_gating_v1_latest.json")
    monkeypatch.setattr(mod, "PHASE2", art / "saving_the_news_phase2_poc_status_v1_latest.json")
    monkeypatch.setattr(mod, "OUT_JSON", art / "out.json")

    doc = mod.build_status()
    assert doc["status"] == "POC_COMPLETE"
    assert doc["exit_criteria"]["roadmap_complete_internal"] is True
