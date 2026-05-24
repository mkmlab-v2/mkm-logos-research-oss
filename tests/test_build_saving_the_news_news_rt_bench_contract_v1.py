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


def test_build_contract_not_measured_by_default() -> None:
    mod = _load(
        "build_saving_the_news_news_rt_bench_contract_v1",
        "scripts/build_saving_the_news_news_rt_bench_contract_v1.py",
    )
    doc = mod.build_contract(
        prerequisite_checks={"news_observation_schema": {"path": "x", "exists": True}}
    )
    assert doc["axis_id"] == "NEWS-RT"
    assert doc["measurement_status"] == "NOT_MEASURED"
    assert doc["kpi_slots"]["token_saving_ratio"] is None
    assert any("A-TRACK" in s for s in doc["forbidden_cross_axis_claims"])


def test_main_writes_artifact(tmp_path, monkeypatch) -> None:
    mod = _load(
        "build_saving_the_news_news_rt_bench_contract_v1",
        "scripts/build_saving_the_news_news_rt_bench_contract_v1.py",
    )
    out = tmp_path / "contract.json"
    monkeypatch.setattr(mod, "OUT_JSON", out)
    assert mod.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "saving_the_news_news_rt_bench_contract_v1"
