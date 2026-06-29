"""Regression: research LIT_REVIEW PMID lock via PubMed (PoC)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_research_lit_review_pmid_lock_v1.py"
FIXTURE = ROOT / "tests/fixtures/research_lit_review_pmid_lock_minimal_v1.md"


def _run(*extra: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPT), "--input", str(FIXTURE), "--offline", *extra]
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)


def test_extract_and_offline_fixture_gate_passes() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.check_research_lit_review_pmid_lock_v1 import (
        build_lock_doc,
        extract_pmids,
        is_valid_pmid_form,
        quote_hash_pmid,
    )

    text = FIXTURE.read_text(encoding="utf-8")
    pmids = extract_pmids(text)
    assert pmids == ["28865470", "25411620", "33564381"]
    assert all(is_valid_pmid_form(p) for p in pmids)
    assert quote_hash_pmid(pmids[0]).startswith("sha256:")

    doc = build_lock_doc(
        source_path=FIXTURE,
        pmids=pmids,
        mode="offline",
        min_pass_rate=0.85,
        min_total_pmids=0,
        verify_results={},
    )
    assert doc["gate_ok"] is True
    assert doc["pmid_pass_rate"] == 1.0
    assert doc["stats"]["total_pmids"] == 3


def test_cli_offline_exit_zero() -> None:
    r = _run("--no-write")
    assert r.returncode == 0, r.stderr + r.stdout
    summary = json.loads(r.stdout.strip())
    assert summary["ok"] is True
    assert summary["total_pmids"] == 3


def test_vacuous_pass_fails_when_min_total_pmids_enforced() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.check_research_lit_review_pmid_lock_v1 import build_lock_doc

    empty = ROOT / "tests/fixtures/research_lit_review_pmid_lock_empty_v1.md"
    empty.write_text("# No PMIDs here\n\nPlain text only.\n", encoding="utf-8")
    try:
        doc = build_lock_doc(
            source_path=empty,
            pmids=[],
            mode="offline",
            min_pass_rate=0.85,
            min_total_pmids=1,
            verify_results={},
        )
        assert doc["gate_ok"] is False
        assert doc["stats"]["total_pmids"] == 0
        assert doc["vacuous_pass"] is False
        assert doc["pmid_pass_rate"] == 0.0
    finally:
        empty.unlink(missing_ok=True)


def test_fetch_resilient_retries_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts import check_research_lit_review_pmid_lock_v1 as mod

    calls: list[list[str]] = []

    def fake_batch(pmids: list[str], **kwargs: object) -> dict[str, dict[str, object]]:
        calls.append(list(pmids))
        if len(calls) == 1:
            return {
                pmids[0]: {"status": "fetch_error", "title": None, "error": "http_429"},
            }
        return {pmids[0]: {"status": "verified", "title": "Example", "error": None}}

    monkeypatch.setattr(mod, "fetch_pubmed_esummary_batch", fake_batch)
    monkeypatch.setattr(mod.time, "sleep", lambda *_: None)
    out = mod.fetch_pubmed_resilient(["28865470"], max_retries=3, retry_sleep=0.01)
    assert out["28865470"]["status"] == "verified"
    assert len(calls) == 2
