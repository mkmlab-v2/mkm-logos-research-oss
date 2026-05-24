from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_run_smoke_fixture_partial_when_contract_exists(tmp_path, monkeypatch) -> None:
    spec = importlib.util.spec_from_file_location(
        "run_saving_the_news_news_rt_bench_smoke_v1",
        ROOT / "scripts/run_saving_the_news_news_rt_bench_smoke_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)

    contract = tmp_path / "contract.json"
    contract.write_text('{"schema":"x"}', encoding="utf-8")
    monkeypatch.setattr(mod, "CONTRACT", contract)
    monkeypatch.setattr(mod, "FIXTURE_NEWS", ROOT / "tests/fixtures/news_observation_v1.sample.jsonl")

    doc = mod.run_smoke()
    assert doc["measurement_status"] == "PARTIAL"
    assert doc["kpi"]["token_saving_ratio"] is None
    assert "A-TRACK" in doc["forbidden_interpretation"][0]
