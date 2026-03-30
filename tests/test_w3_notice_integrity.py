from __future__ import annotations

import json
from pathlib import Path

from scripts.run_w3_resonance_compute import run_compute


ROOT = Path(__file__).resolve().parents[1]
IN_PATH = ROOT / "docs" / "final" / "artifacts" / "W3_PILOT_MIN_INPUT_V1.json"
SPEC_PATH = ROOT / "docs" / "final" / "artifacts" / "W3_RESONANCE_COMPUTE_SPEC_V1.json"
TMP_OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "_w3_notice_integrity_out.json"
TMP_IN = ROOT / "reports" / "constitution" / "btrack_pilot" / "_w3_notice_integrity_in.json"


def _write_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_notice_integrity_passes_with_markers() -> None:
    out = run_compute(IN_PATH, SPEC_PATH, TMP_OUT)
    pg = out.get("promotion_gate") or {}
    assert pg.get("notice_integrity_passed") is True


def test_notice_integrity_fails_when_notice_missing() -> None:
    doc = json.loads(IN_PATH.read_text(encoding="utf-8"))
    personal = (doc.get("personal_lane_samples") or [])[0]
    personal["non_medical_notice"] = "notice removed marker"
    _write_json(TMP_IN, doc)
    out = run_compute(TMP_IN, SPEC_PATH, TMP_OUT)
    pg = out.get("promotion_gate") or {}
    ga = out.get("guardrail_assertions") or {}
    assert pg.get("notice_integrity_passed") is False
    assert pg.get("passed") is False
    assert ga.get("non_medical_notice_present_for_personal_lane") is False
