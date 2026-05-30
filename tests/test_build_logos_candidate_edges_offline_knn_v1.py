"""Smoke: offline 4D kNN candidate edges stay in staging JSONL ([HYPO] B-track)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_candidate_edges_offline_knn_v1.py"
FIXTURE = ROOT / "tests" / "fixtures" / "logos_verse_selective_corpus_min.jsonl"
CANONICAL = ROOT / "docs" / "final" / "artifacts" / "bible_meaning_graph_edges_v1.jsonl"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_logos_candidate_edges_offline_knn_v1", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_build_candidate_edges_from_fixture(tmp_path: Path) -> None:
    mod = _load_module()
    out_jsonl = tmp_path / "candidates.jsonl"
    edges, stats = mod.build_candidate_edges(
        corpus_path=FIXTURE,
        canonical_edges_path=CANONICAL,
        max_verses=10,
        top_k=2,
        min_cosine=0.5,
        max_candidates=20,
        skip_canonical=False,
    )
    assert stats["verses_with_vector_4d"] == 3
    assert len(edges) >= 2
    for edge in edges:
        assert edge["schema"] == "bible_meaning_graph_edge_candidate_v1"
        assert edge["edge_status"] == "candidate"
        assert edge["research_only"] is True
        assert edge["promotion_required"] is True
        assert edge["relation_basis"] == ["offline_4d_knn"]
    out_jsonl.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in edges) + "\n",
        encoding="utf-8",
    )
    assert out_jsonl.read_text(encoding="utf-8").count('"edge_status": "candidate"') == len(edges)


def test_cli_dry_run_smoke(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--corpus-json",
            str(FIXTURE),
            "--report-json",
            str(report),
            "--max-verses",
            "10",
            "--top-k",
            "2",
            "--min-cosine",
            "0.5",
            "--max-candidates",
            "10",
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["schema"] == "logos_candidate_edges_offline_knn_v1"
    assert doc["mode"] == "offline_4d_knn"
    assert doc["track_wall"]["canonical_edges_unmodified"] is True
    assert doc["stats"]["candidate_edges_written"] >= 2


def test_cli_help() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "--max-candidates" in proc.stdout
