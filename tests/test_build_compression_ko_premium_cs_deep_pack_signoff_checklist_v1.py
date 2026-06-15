from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/compression_ko_premium_cs_deep_pack_signoff_checklist_v1_latest.json"
BUILDER = ROOT / "scripts/build_compression_ko_premium_cs_deep_pack_signoff_checklist_v1.py"


def test_build_ko_premium_cs_deep_pack_signoff_checklist_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(BUILDER)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert OUT.is_file()
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_ko_premium_cs_deep_pack_signoff_checklist_v1"
    assert doc["all_green"] is True
    assert doc["decision"] == "READY_FOR_COMMANDER_SIGNOFF"
    assert doc["wire_family"] == "CS_MASK"
    assert doc["checklist"]["mask_token_in_all_catalog_snippets"] is True
    assert doc["constraints"]["human_review_required"] is True
    assert doc["send_gate"] == "HOLD"
