"""zone_a_broadcast_design_dqa_v1 — G0 token + WCAG contrast smoke."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
TOKENS = ROOT / "docs/final/artifacts/zone_a_broadcast_design_tokens_v1.json"
SCHEMA = ROOT / "docs/final/artifacts/schemas/zone_a_broadcast_design_tokens_v1.schema.json"


def test_design_tokens_schema_and_semantic_contrast():
    doc = json.loads(TOKENS.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)

    from scripts.zone_a_broadcast_design_dqa_v1 import (
        audit_semantic_contrast,
        contrast_ratio,
        normalize_hex,
        relative_luminance,
        run_dqa_g0,
        validate_tokens_doc,
    )

    assert validate_tokens_doc(doc) == []
    sem = audit_semantic_contrast(doc)
    assert sem["ok"] is True
    assert all(p["ok"] for p in sem["pairs"])

    # WCAG math spot-check: white on black ≈ 21
    assert contrast_ratio((255, 255, 255), (0, 0, 0)) == pytest.approx(21.0, rel=0.05)
    assert relative_luminance((128, 128, 128)) == pytest.approx(0.22, rel=0.05)

    g0 = run_dqa_g0(tokens_path=TOKENS, skip_preview=True)
    assert g0["g0_pass"] is True
    assert "#FF0000" in {normalize_hex(x) for x in doc["forbidden_hex"]}


def test_forbidden_color_in_semantic_fails():
    from scripts.zone_a_broadcast_design_dqa_v1 import validate_tokens_doc

    doc = json.loads(TOKENS.read_text(encoding="utf-8"))
    doc = json.loads(json.dumps(doc))
    doc["ui_semantic"]["title_on_glass"] = "#FF0000"
    issues = validate_tokens_doc(doc)
    assert any("forbidden" in i or "palette" in i for i in issues)
