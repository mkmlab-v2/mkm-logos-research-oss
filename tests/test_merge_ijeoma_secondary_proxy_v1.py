"""Tests for secondary proxy merge + lit review build."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MERGE = ROOT / "scripts" / "merge_ijeoma_secondary_proxy_to_fragment_ledger_v1.py"
BUILD = ROOT / "scripts" / "build_ijeoma_secondary_proxy_lit_review_v1.py"
PROXY = ROOT / "docs/research/raw/IJEOMA_SECONDARY_PROXY_v1.json"
LEDGER = ROOT / "docs/research/raw/CHEONYUCHO_FRAGMENT_LEDGER_v1.json"
LIT = ROOT / "docs/research/IJEOMA_SECONDARY_PROXY_LIT_REVIEW_2026-06-26.md"
REPORT = ROOT / "reports/constitution/btrack_pilot/ijeoma_secondary_proxy_merge_v1_latest.json"


def test_build_lit_review() -> None:
    cp = subprocess.run(
        [sys.executable, str(BUILD)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    assert LIT.is_file()
    text = LIT.read_text(encoding="utf-8")
    assert "canon_status: not_acquired" in text
    assert "SP-03" in text
    assert "[UNVERIFIED]" in text


def test_merge_proxy_idempotent() -> None:
    cp1 = subprocess.run(
        [sys.executable, str(MERGE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cp1.returncode == 0, cp1.stderr or cp1.stdout
    out1 = json.loads(cp1.stdout.strip().splitlines()[-1])
    assert out1["ok"] is True
    assert REPORT.is_file()

    cp2 = subprocess.run(
        [sys.executable, str(MERGE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cp2.returncode == 0, cp2.stderr or cp.stdout
    out2 = json.loads(cp2.stdout.strip().splitlines()[-1])
    assert out2["ok"] is True
    assert out2["added_count"] == 0
    assert out2["skipped_count"] >= 18

    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    sp_chunks = [c for c in ledger["chunks"] if str(c.get("source_id", "")).startswith("SP-")]
    assert len(sp_chunks) >= 18
    assert all(c.get("canon_claim") is False for c in sp_chunks)
    assert ledger["summary"].get("primary_hanja_chunk_count") == 0
