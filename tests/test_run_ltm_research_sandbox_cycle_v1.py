"""Tests for LTM research sandbox cycle ([HYPO] / B-track)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_ltm_research_sandbox_cycle_v1 import (  # noqa: E402
    _load_contract,
    _validate_concept_draft,
    _validate_seed_id,
)


def test_seed_id_format() -> None:
    assert _validate_seed_id("sandbox_20260613_demo") == []
    assert len(_validate_seed_id("bad_seed")) > 0


def test_concept_draft_kill_matrix() -> None:
    contract = _load_contract(
        ROOT / "docs/final/artifacts/ltm_research_sandbox_cycle_contract_v1.json"
    )
    draft = json.loads(
        (
            ROOT / "docs/final/artifacts/fixtures/ltm_research_concept_draft_v1.example.json"
        ).read_text(encoding="utf-8-sig")
    )
    assert _validate_concept_draft(draft, contract) == []


def test_cycle_dry_run_skip_subprocess() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_ltm_research_sandbox_cycle_v1.py"),
            "--seed-id",
            "sandbox_20260613_pytest",
            "--dry-run",
            "--skip-ingest-subprocess",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr


def test_record_signoff_requires_ack() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/record_ltm_research_sandbox_human_signoff_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
