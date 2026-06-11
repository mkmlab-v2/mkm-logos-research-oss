"""Open-sandbox virtual tenant corpus builder smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TENANT = "open-sandbox-01-test"


def test_build_open_sandbox_corpus() -> None:
    golden = ROOT / "data/compression/stateless_poc_golden40_public_safe_v1.jsonl"
    if not golden.is_file():
        pytest.skip("golden40 public-safe corpus missing")
    out = ROOT / f"data/compression/stateless_poc_open_sandbox_{TENANT}_v1.jsonl"
    if out.is_file():
        out.unlink()
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/build_compression_open_sandbox_corpus_v1.py",
            "--tenant-id",
            TENANT,
            "--max-cases",
            "5",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert out.is_file()
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 5
    row = json.loads(lines[0])
    assert row.get("tenant_id") == TENANT
    assert row.get("virtual_tenant") is True
    assert row.get("solo_self_audit_only") is True
