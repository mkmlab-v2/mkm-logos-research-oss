"""Regression: explore → LIT_REVIEW builder (P1)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_JSONL = ROOT / "tests/fixtures/mkm_deep_explore_sample_v1.jsonl"
BUILD = ROOT / "scripts/build_mkm_deep_explore_lit_review_v1.py"
CHAIN = ROOT / "scripts/run_mkm_deep_explore_lit_review_chain_v1.py"


def test_build_lit_review_from_fixture(tmp_path: Path) -> None:
    out = tmp_path / "memory_os_LIT_REVIEW_2026-06-20.md"
    r = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--jsonl",
            str(FIXTURE_JSONL),
            "--query",
            "memory OS",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(r.stdout.strip())
    assert doc["arxiv_id_count"] == 2
    text = out.read_text(encoding="utf-8")
    assert "2506.11763" in text
    assert "2310.08560" in text
    assert "Repo crosswalk" in text


def test_chain_skip_explore_offline(tmp_path: Path) -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(CHAIN),
            "--query",
            "memory OS",
            "--jsonl",
            str(FIXTURE_JSONL),
            "--skip-explore",
            "--offline",
            "--out-json",
            str(tmp_path / "chain.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    chain_doc = json.loads((tmp_path / "chain.json").read_text(encoding="utf-8"))
    assert chain_doc["ok"] is True
    assert chain_doc["citation_lock"]["ok"] is True
