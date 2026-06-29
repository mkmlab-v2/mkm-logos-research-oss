"""Discrimination report builder."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_clinic_survey_discrimination_report_v1 import build_report

ROOT = Path(__file__).resolve().parent.parent


def test_build_report_on_live_ledger() -> None:
    clinic = ROOT / "data" / "clinic"
    paths = sorted(clinic.glob("clinic_constitution_mvp_v1*.jsonl"))
    records = []
    for p in paths:
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
    report = build_report(records)
    assert report["schema"] == "clinic_survey_discrimination_report_v1"
    assert report["n_ledger_rows"] >= 10
    assert "consumer_survey_ai" in report["distribution"]
