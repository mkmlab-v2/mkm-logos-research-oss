from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/compression_deep_pack_tri_vertical_post_signoff_checklist_v1_latest.json"
BUILDER = ROOT / "scripts/build_compression_deep_pack_tri_vertical_post_signoff_checklist_v1.py"
TRI_SIGNOFF = ROOT / "reports/compression_deep_pack_tri_vertical_human_signoff_latest.json"


def test_build_post_signoff_checklist_when_commander_signed() -> None:
    if not TRI_SIGNOFF.is_file():
        import pytest

        pytest.skip("tri human signoff record missing")
    from scripts.compression_deep_pack_tri_vertical_human_signoff_v1_lib import reconcile_from_tri_signoff_record

    reconcile_from_tri_signoff_record()
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
    assert doc["schema"] == "compression_deep_pack_tri_vertical_post_signoff_checklist_v1"
    assert doc["all_green"] is True
    assert doc["decision"] == "COMMANDER_SIGNED_RESEARCH_ENVELOPE_ONLY"
    assert doc["checklist"]["all_child_envelopes_commander_signed"] is True
    assert doc["send_gate"] == "HOLD"
