from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from scripts.route_prompt_codebook_instincts_v1 import _load_json, route_instincts

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/final/schemas/prompt_codebook_instinct_v0.schema.json"
CODEBOOK = ROOT / "docs/final/artifacts/prompt_codebook_instincts_v0.json"
GOLDEN = ROOT / "docs/final/artifacts/fixtures/prompt_codebook_golden_v0.jsonl"


def test_codebook_schema_valid():
    doc = _load_json(CODEBOOK)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)
    assert len(doc["instincts"]) >= 20


def test_crisis_routes_safety_handoff():
    report = route_instincts(
        user_text="너무 힘들어서 죽고 싶어.",
        codebook=_load_json(CODEBOOK),
    )
    assert "inst_safety_crisis_handoff" in report["selected_instinct_ids"]


def test_golden_v0_expectations():
    codebook = _load_json(CODEBOOK)
    failures: list[str] = []
    for line in GOLDEN.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        report = route_instincts(user_text=row["text"], codebook=codebook)
        selected = set(report["selected_instinct_ids"])
        for needle in row.get("expect_contains") or []:
            if needle == "inst_wellness":
                if not any(i.startswith("inst_wellness") for i in selected):
                    failures.append(f"{row['id']}: missing wellness family in {selected}")
            elif needle == "inst_cs":
                if not any(i.startswith("inst_cs") for i in selected):
                    failures.append(f"{row['id']}: missing cs family in {selected}")
            elif needle == "inst_audit":
                if "inst_audit_log_hint" not in selected:
                    failures.append(f"{row['id']}: missing audit in {selected}")
            elif needle not in selected:
                failures.append(f"{row['id']}: expected {needle} in {selected}")
    assert not failures, "\n".join(failures)
