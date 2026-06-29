"""Regression: research LIT_REVIEW arXiv citation lock (Phase A)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_research_lit_review_citation_lock_v1.py"
FIXTURE = ROOT / "tests/fixtures/research_lit_review_citation_lock_minimal_v1.md"


def _run(*extra: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPT), "--input", str(FIXTURE), "--offline", *extra]
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)


def test_extract_and_offline_fixture_gate_passes() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.check_research_lit_review_citation_lock_v1 import (
        build_lock_doc,
        extract_arxiv_ids,
        is_valid_arxiv_id_form,
        quote_hash_arxiv,
    )

    text = FIXTURE.read_text(encoding="utf-8")
    ids = extract_arxiv_ids(text)
    assert ids == ["2506.11763", "2310.08560", "2403.12031"]
    assert all(is_valid_arxiv_id_form(i) for i in ids)
    assert quote_hash_arxiv("2506.11763").startswith("sha256:")

    doc = build_lock_doc(
        source_path=FIXTURE,
        arxiv_ids=ids,
        mode="offline",
        min_pass_rate=0.85,
        min_total_ids=0,
        verify_results={},
    )
    assert doc["gate_ok"] is True
    assert doc["citation_pass_rate"] == 1.0
    assert doc["stats"]["total_ids"] == 3


def test_cli_offline_exit_zero() -> None:
    r = _run("--stdout-only", "--no-write")
    assert r.returncode == 0, r.stderr + r.stdout
    summary = json.loads(r.stdout.strip())
    assert summary["ok"] is True
    assert summary["mode"] == "offline"
    assert summary["files"][0]["total_ids"] == 3


def test_cli_online_fixture_verified(monkeypatch) -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts import check_research_lit_review_citation_lock_v1 as mod

    def fake_batch(ids: list[str], *, timeout: float = 20.0) -> dict[str, dict]:
        return {aid: {"status": "verified", "title": f"title-{aid}", "error": None} for aid in ids}

    monkeypatch.setattr(mod, "fetch_arxiv_metadata_batch", fake_batch)
    doc = mod.check_file(
        FIXTURE,
        mode="online",
        min_pass_rate=0.85,
        min_total_ids=0,
        out_dir=ROOT / "docs/final/artifacts",
        write_out=False,
    )
    assert doc["gate_ok"] is True
    assert doc["citation_pass_rate"] == 1.0
    assert doc["stats"]["verified"] == 3


def test_invalid_format_fails_gate() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.check_research_lit_review_citation_lock_v1 import build_lock_doc

    doc = build_lock_doc(
        source_path=FIXTURE,
        arxiv_ids=["9999.99999"],
        mode="offline",
        min_pass_rate=0.85,
        min_total_ids=0,
        verify_results={},
    )
    assert doc["gate_ok"] is False
    assert doc["entries"][0]["status"] == "invalid_format"


def test_vacuous_pass_fails_when_min_total_ids_enforced() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.check_research_lit_review_citation_lock_v1 import build_lock_doc

    empty = ROOT / "tests/fixtures/research_lit_review_citation_lock_empty_v1.md"
    empty.write_text("# No arXiv IDs here\n\nPlain text only.\n", encoding="utf-8")
    try:
        doc = build_lock_doc(
            source_path=empty,
            arxiv_ids=[],
            mode="offline",
            min_pass_rate=0.85,
            min_total_ids=1,
            verify_results={},
        )
        assert doc["gate_ok"] is False
        assert doc["stats"]["total_ids"] == 0
        assert doc["vacuous_pass"] is False
        assert doc["citation_pass_rate"] == 0.0
    finally:
        empty.unlink(missing_ok=True)


def test_fetch_resilient_retries_rate_limit(monkeypatch) -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts import check_research_lit_review_citation_lock_v1 as mod

    calls: list[list[str]] = []

    def fake_batch(ids: list[str], *, timeout: float = 20.0) -> dict[str, dict]:
        calls.append(list(ids))
        if len(calls) == 1:
            return {
                aid: {"status": "fetch_error", "title": None, "error": "HTTP Error 429: Too Many Requests"}
                for aid in ids
            }
        return {aid: {"status": "verified", "title": f"t-{aid}", "error": None} for aid in ids}

    monkeypatch.setattr(mod, "fetch_arxiv_metadata_batch", fake_batch)
    monkeypatch.setattr(mod.time, "sleep", lambda _s: None)
    out = mod.fetch_arxiv_metadata_resilient(["2506.11763"], batch_size=1, max_retries=3)
    assert out["2506.11763"]["status"] == "verified"
    assert len(calls) == 2
