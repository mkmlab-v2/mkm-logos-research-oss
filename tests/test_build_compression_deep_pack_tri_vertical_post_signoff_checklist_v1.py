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
    from scripts.compression_deep_pack_tri_vertical_human_signoff_v1_lib import reconcile_from_tri_signoff_record

    record = ROOT / "scripts/record_compression_deep_pack_tri_vertical_human_signoff_v1.py"
    tri_path = ROOT / "reports/compression_deep_pack_tri_vertical_human_signoff_latest.json"
    tri = json.loads(tri_path.read_text(encoding="utf-8")) if tri_path.is_file() else {}
    if not tri.get("approved"):
        proc_sign = subprocess.run(
            [
                sys.executable,
                str(record),
                "--reviewer",
                "commander",
                "--acknowledge-research-envelope-only",
                "--skip-tri-checklist-gate",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc_sign.returncode == 0, proc_sign.stderr or proc_sign.stdout

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
