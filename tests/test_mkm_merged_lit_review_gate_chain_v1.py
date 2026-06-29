"""Regression: MERGED SSOT recommended gate chain."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/research_lit_review_citation_lock_minimal_v1.md"
CHAIN = ROOT / "scripts/run_mkm_merged_lit_review_gate_chain_v1.py"
ROUTER_SHALLOW = ROOT / "scripts/build_mkm_research_router_to_shallow_v1.py"
ROUTER_INDEX = ROOT / "docs/final/artifacts/hybrid_edge_cloud_llm_memory_research_router_index_latest.json"


def test_merged_gate_chain_offline_fixture(tmp_path: Path) -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(CHAIN),
            "--input",
            str(FIXTURE),
            "--query",
            "memory OS benchmark",
            "--offline",
            "--out-json",
            str(tmp_path / "gate.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads((tmp_path / "gate.json").read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["min_total_ids"] == 1
    assert doc["min_total_claims"] == 1
    assert doc["citation_lock"]["ok"] is True
    assert doc["citation_lock"]["min_total_ids"] == 1
    assert doc["citation_lock"]["files"][0]["vacuous_pass"] is False
    assert doc["fact_support"]["ok"] is True
    assert doc["fact_support"]["min_total_claims"] == 1
    assert doc["fact_support"]["total_claims"] >= 1
    assert doc["router_index"]["arxiv_id_count"] == 3
    assert doc["doi_lock_enabled"] is True
    assert doc["doi_lock"]["skipped"] is True
    assert doc["doi_lock"]["reason"] == "no_dois_in_source"
    assert doc["pmid_lock_enabled"] is True
    assert doc["pmid_lock"]["skipped"] is True
    assert doc["pmid_lock"]["reason"] == "no_pmids_in_source"


def test_merged_gate_chain_dual_citation_runs_doi_lock(tmp_path: Path) -> None:
    dual = ROOT / "tests/fixtures/research_lit_review_dual_citation_minimal_v1.md"
    r = subprocess.run(
        [
            sys.executable,
            str(CHAIN),
            "--input",
            str(dual),
            "--query",
            "memory OS benchmark",
            "--offline",
            "--skip-handoff",
            "--out-json",
            str(tmp_path / "gate_dual.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads((tmp_path / "gate_dual.json").read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["citation_lock"]["ok"] is True
    assert doc["doi_lock"]["ok"] is True
    assert doc["doi_lock"].get("skipped") is not True
    assert doc["doi_lock"]["total_dois"] == 1
    assert doc["pmid_lock"]["ok"] is True
    assert doc["pmid_lock"].get("skipped") is not True
    assert doc["pmid_lock"]["total_pmids"] == 2


def test_merged_gate_chain_skip_doi_lock_flag(tmp_path: Path) -> None:
    dual = ROOT / "tests/fixtures/research_lit_review_dual_citation_minimal_v1.md"
    r = subprocess.run(
        [
            sys.executable,
            str(CHAIN),
            "--input",
            str(dual),
            "--query",
            "memory OS benchmark",
            "--offline",
            "--skip-handoff",
            "--skip-doi-lock",
            "--out-json",
            str(tmp_path / "gate_no_doi.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads((tmp_path / "gate_no_doi.json").read_text(encoding="utf-8"))
    assert doc["doi_lock_enabled"] is False
    assert doc["doi_lock"] is None
    assert doc["pmid_lock_enabled"] is True
    assert doc["pmid_lock"]["ok"] is True


def test_merged_gate_chain_skip_pmid_lock_flag(tmp_path: Path) -> None:
    dual = ROOT / "tests/fixtures/research_lit_review_dual_citation_minimal_v1.md"
    r = subprocess.run(
        [
            sys.executable,
            str(CHAIN),
            "--input",
            str(dual),
            "--query",
            "memory OS benchmark",
            "--offline",
            "--skip-handoff",
            "--skip-pmid-lock",
            "--out-json",
            str(tmp_path / "gate_no_pmid.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads((tmp_path / "gate_no_pmid.json").read_text(encoding="utf-8"))
    assert doc["pmid_lock_enabled"] is False
    assert doc["pmid_lock"] is None


def test_merged_gate_chain_vacuous_citation_fails_by_default(tmp_path: Path) -> None:
    empty_md = tmp_path / "no_arxiv.md"
    empty_md.write_text("# Plain note\n\nNo citations here.\n", encoding="utf-8")
    r = subprocess.run(
        [
            sys.executable,
            str(CHAIN),
            "--input",
            str(empty_md),
            "--query",
            "noop",
            "--offline",
            "--skip-handoff",
            "--out-json",
            str(tmp_path / "gate_fail.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0, r.stderr + r.stdout
    payload = json.loads(r.stdout.strip() or "{}")
    assert payload.get("step") == "citation_lock"


def test_router_to_shallow_with_handoff(tmp_path: Path) -> None:
    if not ROUTER_INDEX.is_file():
        return
    shallow_out = tmp_path / "shallow.json"
    handoff_out = tmp_path / "handoff.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROUTER_SHALLOW),
            "--input",
            str(ROUTER_INDEX),
            "--out",
            str(shallow_out),
            "--with-handoff",
            "--handoff-out",
            str(handoff_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    shallow = json.loads(shallow_out.read_text(encoding="utf-8"))
    assert shallow["schema"] == "ollama_shallow_router_output_v1"
    assert shallow["domain_tag"] in {"infra", "oracle", "devops", "design"}
    handoff = json.loads(handoff_out.read_text(encoding="utf-8"))
    assert handoff["schema"] == "ollama_shallow_router_handoff_v1"
