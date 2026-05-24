from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "run_saving_the_news_news_rt_bench_v1",
        ROOT / "scripts/run_saving_the_news_news_rt_bench_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_run_bench_complete_on_fixture_expanded(tmp_path) -> None:
    mod = _load()
    src = ROOT / "docs/final/artifacts/news_observation_v1_latest.jsonl"
    assert src.is_file()
    lines = src.read_text(encoding="utf-8").splitlines()
    # duplicate lines to reach min_rows without inventing schema
    expanded = tmp_path / "cohort.jsonl"
    need = 120
    buf: list[str] = []
    i = 0
    while len(buf) < need:
        buf.append(lines[i % len(lines)])
        i += 1
    expanded.write_text("\n".join(buf) + "\n", encoding="utf-8")

    doc = mod.run_bench(expanded, min_rows=120)
    assert doc["measurement_status"] == "COMPLETE"
    assert doc["observation_row_count"] == 120
    assert doc["kpi"]["token_saving_ratio"] is not None
    assert doc["kpi"]["jaccard_fidelity_proxy"] is not None
    assert doc["status"] == "OFFLINE_COHORT_BENCH"


def test_cohort_too_small() -> None:
    mod = _load()
    doc = mod.run_bench(ROOT / "tests/fixtures/news_observation_v1.sample.jsonl", min_rows=120)
    assert doc["measurement_status"] == "NOT_MEASURED"
    assert doc["status"] == "COHORT_TOO_SMALL"
