"""Regression: research LIT_REVIEW DOI lock via Crossref (PoC)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_research_lit_review_doi_lock_v1.py"
FIXTURE = ROOT / "tests/fixtures/research_lit_review_doi_lock_minimal_v1.md"


def _run(*extra: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPT), "--input", str(FIXTURE), "--offline", *extra]
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)


def test_extract_and_offline_fixture_gate_passes() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.check_research_lit_review_doi_lock_v1 import (
        build_lock_doc,
        extract_dois,
        is_valid_doi_form,
        quote_hash_doi,
    )

    text = FIXTURE.read_text(encoding="utf-8")
    dois = extract_dois(text)
    assert dois == [
        "10.1186/s12906-017-1936-4",
        "10.1111/jdi.12189",
        "10.1016/j.eujim.2013.05.003",
    ]
    assert all(is_valid_doi_form(d) for d in dois)
    assert quote_hash_doi(dois[0]).startswith("sha256:")

    doc = build_lock_doc(
        source_path=FIXTURE,
        dois=dois,
        mode="offline",
        min_pass_rate=0.85,
        min_total_dois=0,
        verify_results={},
    )
    assert doc["gate_ok"] is True
    assert doc["doi_pass_rate"] == 1.0
    assert doc["stats"]["total_dois"] == 3


def test_cli_offline_exit_zero() -> None:
    r = _run("--no-write")
    assert r.returncode == 0, r.stderr + r.stdout
    summary = json.loads(r.stdout.strip())
    assert summary["ok"] is True
    assert summary["total_dois"] == 3


def test_vacuous_pass_fails_when_min_total_dois_enforced() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.check_research_lit_review_doi_lock_v1 import build_lock_doc

    empty = ROOT / "tests/fixtures/research_lit_review_doi_lock_empty_v1.md"
    empty.write_text("# No DOIs here\n\nPlain text only.\n", encoding="utf-8")
    try:
        doc = build_lock_doc(
            source_path=empty,
            dois=[],
            mode="offline",
            min_pass_rate=0.85,
            min_total_dois=1,
            verify_results={},
        )
        assert doc["gate_ok"] is False
        assert doc["stats"]["total_dois"] == 0
        assert doc["vacuous_pass"] is False
        assert doc["doi_pass_rate"] == 0.0
    finally:
        empty.unlink(missing_ok=True)


def test_fetch_resilient_retries_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts import check_research_lit_review_doi_lock_v1 as mod

    calls: list[str] = []

    def fake_fetch(doi: str, **kwargs: object) -> dict[str, object]:
        calls.append(doi)
        if len(calls) == 1:
            return {"status": "fetch_error", "title": None, "error": "http_429"}
        return {"status": "verified", "title": "Example", "error": None}

    monkeypatch.setattr(mod, "fetch_crossref_work", fake_fetch)
    monkeypatch.setattr(mod.time, "sleep", lambda *_: None)
    out = mod.fetch_crossref_resilient(["10.1186/s12906-017-1936-4"], max_retries=3, retry_sleep=0.01)
    assert out["10.1186/s12906-017-1936-4"]["status"] == "verified"
    assert len(calls) == 2
