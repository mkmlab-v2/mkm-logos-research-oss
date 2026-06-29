from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def test_load_theme_preset_dan() -> None:
    from scripts.logos_deep_research_graph_evidence_v1 import load_theme_preset

    p = load_theme_preset("dan_aramaic")
    assert p["verse_prefix"] == "Dan.2."


def test_jhn1_sequential_fallback(tmp_path: Path) -> None:
    from scripts.logos_deep_research_graph_evidence_v1 import build_enriched_distill_fields

    bundle = _ROOT / "tests/fixtures/logos_corpus_graph_bundle_minimal_distill_v1.json"
    out_fields = build_enriched_distill_fields(
        bundle_path=bundle,
        theme_id="john_1_logos",
        edges_path=tmp_path / "empty_edges.jsonl",
    )
    assert len(out_fields.get("graph_paths") or []) >= 2
    assert len(out_fields.get("evidence_refs") or []) >= 3
    refs = out_fields["evidence_refs"]
    assert any(str(r.get("verse_id", "")).startswith("Jhn.1.") for r in refs)


def test_citation_lock_requires_flag() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/run_logos_llm_distill_citation_lock_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 2


def test_citation_lock_applies(tmp_path: Path) -> None:
    distill_in = tmp_path / "in.json"
    distill_in.write_text(
        json.dumps(
            {
                "evidence_refs": [
                    {"verse_id": "Jhn.1.1", "quote_hash": "sha256:abc"},
                    {"verse_id": "Jhn.1.2", "quote_hash": "sha256:def"},
                ]
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/run_logos_llm_distill_citation_lock_v1.py"),
            "--allow-llm-distill",
            "--input",
            str(distill_in),
            "--output",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["citation_lock"]["locked_count"] == 2
    assert doc["distill_narrative_stub_ko"]["llm_invoked"] is False


def test_validate_citations_orphan() -> None:
    from scripts.run_logos_llm_distill_citation_lock_v1 import _validate_citations

    v = _validate_citations("Jhn.1.1 says [HYPO] and Jhn.9.9 wrong", {"Jhn.1.1"})
    assert v["citation_valid"] is False
    assert "Jhn.9.9" in v["orphan_citations"]
