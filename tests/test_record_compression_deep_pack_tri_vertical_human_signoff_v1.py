from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "scripts/record_compression_deep_pack_tri_vertical_human_signoff_v1.py"
OUT = ROOT / "reports/compression_deep_pack_tri_vertical_human_signoff_latest.json"


def _reset_child_envelopes_for_signoff() -> None:
    for script in (
        "build_compression_coding_deep_pack_gate_v1.py",
        "build_compression_en_business_deep_pack_gate_v1.py",
        "build_compression_ko_premium_cs_deep_pack_gate_v1.py",
    ):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / script)], cwd=ROOT, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr or proc.stdout
    for script in (
        "build_compression_coding_deep_pack_signoff_checklist_v1.py",
        "build_compression_en_business_deep_pack_signoff_checklist_v1.py",
        "build_compression_ko_premium_cs_deep_pack_signoff_checklist_v1.py",
    ):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / script)], cwd=ROOT, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr or proc.stdout
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_compression_deep_pack_tri_vertical_signoff_checklist_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    tri = json.loads(
        (ROOT / "docs/final/artifacts/compression_deep_pack_tri_vertical_signoff_checklist_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert tri["all_green"] is True


def test_record_tri_vertical_signoff_denied_without_ack() -> None:
    proc = subprocess.run(
        [sys.executable, str(RECORD), "--reviewer", "commander_test"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2


def test_record_tri_vertical_signoff_approve(tmp_path: Path) -> None:
    _reset_child_envelopes_for_signoff()
    out = tmp_path / "signoff.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(RECORD),
            "--out-json",
            str(out),
            "--reviewer",
            "commander_test",
            "--note",
            "tri-vertical research envelope only",
            "--acknowledge-research-envelope-only",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["approved"] is True
    assert doc["decision"] == "APPROVED_RESEARCH_ENVELOPE_ONLY"
    assert doc["research_envelope_only_acknowledged"] is True
    assert len(doc.get("patched_child_envelopes") or []) >= 3
