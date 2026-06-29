"""build_encounter_sequence_summary_v1 — aggregate KPI smoke."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_encounter_sequence_summary_v1 import build

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data/clinic/encounter_sequence_v1.sample.jsonl"


def test_summary_from_sample() -> None:
    doc = build(paths=[SAMPLE])
    assert doc.get("summary_ok") is True
    assert int(doc.get("sequence_count") or 0) >= 1
    assert doc.get("domain_lane") == "tkm_korean_han_medicine"
    assert doc.get("physician_agreement_rate") is not None


def test_summary_writes_report(tmp_path: Path, monkeypatch) -> None:
    out = tmp_path / "encounter_sequence_summary_v1_latest.json"
    import scripts.build_encounter_sequence_summary_v1 as mod

    monkeypatch.setattr(mod, "OUT", out)
    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_encounter_sequence_summary_v1.py"), "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "encounter_sequence_summary_v1"
