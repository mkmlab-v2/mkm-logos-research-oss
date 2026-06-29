"""commander_a_code_promotion_rq_ack_v1 validator tests."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "data/personalization/commander_a_code_promotion_rq_ack_v1.local.json.example"
SCHEMA = ROOT / "docs/final/schemas/commander_a_code_promotion_rq_ack_v1.schema.json"


def _load_validator():
    path = ROOT / "scripts/validate_commander_a_code_promotion_rq_ack_v1.py"
    spec = importlib.util.spec_from_file_location("validate_promotion_rq_ack", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_example_ack_schema_valid() -> None:
    mod = _load_validator()
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    errors = mod.validate_ack_doc(doc, schema_path=SCHEMA)
    assert errors == []
    assert doc.get("acknowledged") is False


def test_acknowledged_requires_scope_and_reference() -> None:
    mod = _load_validator()
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    doc["acknowledged"] = True
    doc["ack_utc"] = "2026-06-05T10:00:00Z"
    doc["ack_reference"] = "COMMANDER-RQ031-SCOPE-ACK-2026-06-05"
    errors = mod.validate_ack_doc(doc, schema_path=SCHEMA)
    assert any("operator_assist_trackc_only" in e for e in errors)


def test_acknowledged_passes_when_scope_true() -> None:
    mod = _load_validator()
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    doc["acknowledged"] = True
    doc["ack_utc"] = "2026-06-05T10:00:00Z"
    doc["ack_reference"] = "COMMANDER-RQ031-SCOPE-ACK-2026-06-05"
    doc["scope_confirmed"] = {
        "operator_assist_trackc_only": True,
        "no_track_a_live_ms_merge": True,
        "separate_pr_for_constitution": True,
    }
    errors = mod.validate_ack_doc(doc, schema_path=SCHEMA)
    assert errors == []
    summary = mod.ack_summary(doc, errors=errors)
    assert summary["promotion_rq_ack_status"] == "ACKNOWLEDGED"
