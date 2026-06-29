"""Regression: P2 router index + FACT Phase B support judge."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_JSONL = ROOT / "tests/fixtures/mkm_deep_explore_sample_v1.jsonl"
ROUTER = ROOT / "scripts/build_mkm_deep_research_router_index_v1.py"
FACT = ROOT / "scripts/check_research_lit_review_fact_support_v1.py"
CHAIN = ROOT / "scripts/run_mkm_deep_explore_lit_review_chain_v1.py"


def test_router_classifies_tcm_citation_as_benchmarks() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.build_mkm_deep_research_router_index_v1 import classify_research_plane, load_jsonl

    jsonl = ROOT / "tests/fixtures/dr_bench_mini/herbs_formulas_tcm_v1.jsonl"
    rows = load_jsonl(jsonl)
    plane = classify_research_plane(
        query="herbs formulas TCM citation verification workflow",
        rows=rows,
    )
    assert plane == "research_benchmarks"


def test_router_index_from_fixture(tmp_path: Path) -> None:
    out = tmp_path / "memory_os_research_router_index_latest.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROUTER),
            "--jsonl",
            str(FIXTURE_JSONL),
            "--query",
            "memory OS hybrid",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(r.stdout.strip())
    assert doc["research_plane"] in {
        "research_memory",
        "research_edge",
        "research_benchmarks",
        "research_meta",
    }
    assert doc["row_count"] == 3
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["schema"] == "mkm_deep_research_router_index_v1"
    assert len(saved["arxiv_ids"]) == 2


def test_fact_support_offline_jsonl(tmp_path: Path) -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(FACT),
            "--jsonl",
            str(FIXTURE_JSONL),
            "--offline",
            "--no-write",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    summary = json.loads(r.stdout.strip())
    assert summary["ok"] is True
    assert summary["total_claims"] == 2


def test_fact_support_online_mock(monkeypatch) -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts import check_research_lit_review_fact_support_v1 as mod

    def fake_batch(ids: list[str], *, timeout: float = 20.0) -> dict[str, dict]:
        titles = {
            "2506.11763": "DeepResearch Bench: Evaluating Deep Research Agents",
            "2310.08560": "MemGPT: Towards LLMs as Operating Systems",
        }
        return {
            aid: {
                "status": "fetched",
                "title": titles.get(aid, f"title-{aid}"),
                "abstract": "We introduce DeepResearch Bench for agent evaluation and memory systems.",
                "error": None,
            }
            for aid in ids
        }

    monkeypatch.setattr(mod, "fetch_arxiv_records_batch", fake_batch)
    doc = mod.check_fact_support(
        lit_md=None,
        jsonl=FIXTURE_JSONL,
        mode="online",
        min_pass_rate=0.85,
        out_dir=ROOT / "docs/final/artifacts",
        write_out=False,
    )
    assert doc["gate_ok"] is True
    assert doc["support_pass_rate"] == 1.0


def test_chain_include_p2_offline(tmp_path: Path) -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(CHAIN),
            "--query",
            "memory OS",
            "--jsonl",
            str(FIXTURE_JSONL),
            "--skip-explore",
            "--include-p2",
            "--offline",
            "--out-json",
            str(tmp_path / "chain_p2.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    chain_doc = json.loads((tmp_path / "chain_p2.json").read_text(encoding="utf-8"))
    assert chain_doc["ok"] is True
    assert chain_doc["chain_version"] == "1.1.0"
    assert chain_doc["router_index"]["research_plane"]
    assert chain_doc["fact_support"]["ok"] is True
