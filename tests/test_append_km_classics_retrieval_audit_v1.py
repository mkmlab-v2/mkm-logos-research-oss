"""D3: km classics retrieval audit JSONL tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from append_km_classics_retrieval_audit_v1 import (  # noqa: E402
    SCHEMA,
    append_audit_row,
    build_audit_row,
)


def test_audit_row_has_no_patient_fields(tmp_path: Path) -> None:
    row = build_audit_row(
        retrieval_query="donguibogam",
        source_ids_requested=["kmc-stub-1"],
        hit_source_ids=["kmc-stub-1"],
        index_path="tests/fixtures/km_classics_index_hypo_v1.stub.json",
        bundle_id="bundle-test",
        request_id="req-test",
    )
    assert row["schema"] == SCHEMA
    assert row["clinician_lane_only"] is True
    assert row["personadiary_join"] is False
    assert row["on_demand_only"] is True
    forbidden_keys = {"patient_slots", "clinical_soap_v1", "subjective", "chief_complaint", "body_markdown"}
    assert forbidden_keys.isdisjoint(row.keys())
    blob = json.dumps(row, ensure_ascii=False)
    assert "chief_complaint" not in blob
    assert "SOAP" not in blob

    out = tmp_path / "audit.jsonl"
    append_audit_row(out, row)
    line = out.read_text(encoding="utf-8").strip()
    parsed = json.loads(line)
    assert parsed["hit_source_ids"] == ["kmc-stub-1"]
