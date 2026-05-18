"""Phase 3 leading sensors chain — manifest validation."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.run_btrack_phase3_leading_sensors_chain_v1 import _manifest_ok

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/final/artifacts/btrack_phase3_leading_sensors_manifest_v1.json"


def test_manifest_valid() -> None:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert _manifest_ok(doc) == []


def test_manifest_dry_run_exit_code() -> None:
    from scripts.run_btrack_phase3_leading_sensors_chain_v1 import main

    assert main(["--dry-run"]) == 0
