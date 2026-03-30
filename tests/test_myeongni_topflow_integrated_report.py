# @MKM12-METADATA
# Type: Logic
# Purpose: Validate integrated topflow interpretation report contract.
# Keywords: myeongni, topflow, integrated, report

from __future__ import annotations

import json
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_REPORT = _ROOT / "docs" / "final" / "artifacts" / "MYEONGNI_TOPFLOW_INTEGRATED_REPORT_V1.json"


def test_integrated_report_schema_and_sources() -> None:
    assert _REPORT.is_file(), f"missing report: {_REPORT}"
    doc = json.loads(_REPORT.read_text(encoding="utf-8"))
    assert doc.get("schema") == "myeongni_topflow_integrated_report_v1"
    assert isinstance(doc.get("generated_at_utc"), str) and doc["generated_at_utc"].strip()
    sources = doc.get("sources", {})
    assert sources.get("topflow_interpretation") == "docs/final/artifacts/MYEONGNI_16_STATE_TOPFLOW_INTERPRETATION_V1.json"
    assert sources.get("entry16_gate") == "docs/final/artifacts/entry16_promotion_gate.json"


def test_integrated_report_guardrails() -> None:
    doc = json.loads(_REPORT.read_text(encoding="utf-8"))
    core = doc.get("core_readout", {})
    assert isinstance(core.get("one_line"), str)
    assert core.get("quality_stage") in {"bootstrap_insufficient_rows", "analysis_ready", "unknown"}
    assert core.get("entry16_gate_decision") in {
        "keep_locked",
        "promote_candidate",
        "promote_proxy_candidate_manual",
    }
    assert doc.get("operational_call") in {"analysis_read_only_continue", "analysis_ready_expand"}
    guardrails = doc.get("guardrails", [])
    assert isinstance(guardrails, list) and guardrails
