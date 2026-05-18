"""DSS slot mapping refresh pack (full vs canonical)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_logos_dss_slot_mapping_refresh_pack_v1.py"
DSS = ROOT / "data/logos/manuscripts/dss_parsed_enriched.jsonl"
PACK = ROOT / "docs/final/artifacts/logos_dss_slot_mapping_refresh_pack_v1_latest.json"


@pytest.mark.skipif(not DSS.is_file(), reason="dss enriched missing")
def test_slot_mapping_refresh_pack_smoke() -> None:
    rc = subprocess.run(
        [sys.executable, str(SCRIPT), "--skip-strict-audit"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert rc.returncode == 0, rc.stderr or rc.stdout
    assert PACK.is_file()
    doc = json.loads(PACK.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_dss_slot_mapping_refresh_pack_v1"
    assert doc["canonical_filter"].get("kept_rows", 0) >= 1
