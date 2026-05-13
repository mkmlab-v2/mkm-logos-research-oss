"""Smoke tests for build_semantic_rag_bridge_insight_bundle_v1 CLI builder."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_build_bundle_defaults_validate(tmp_path: Path) -> None:
    from scripts.build_semantic_rag_bridge_insight_bundle_v1 import build_bundle

    bundle = build_bundle(
        calibration_kind="none",
        calibration_artifact=None,
        summary_line=None,
        rag_evidence=[],
        structured_slots=None,
        lens_id="logos",
        route_confidence=0.7,
        track="B-track",
        gating="NON_GATING",
        hypothesis_label="[HYPO]",
    )
    schema = json.loads(
        (ROOT / "docs/final/schemas/semantic_rag_bridge_insight_bundle_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.validate(instance=bundle, schema=schema)
    out = tmp_path / "bundle.json"
    out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    assert out.is_file()


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_build_bundle_with_rag_and_calibration_path(tmp_path: Path) -> None:
    from scripts.build_semantic_rag_bridge_insight_bundle_v1 import build_bundle

    fake = tmp_path / "snap.json"
    fake.write_text('{"note": "fixture"}\n', encoding="utf-8")
    rag = [
        {"source_id": "c1", "snippet": "hello " * 10, "confidence_band": "A"},
    ]
    bundle = build_bundle(
        calibration_kind="logos_4d_state_v1",
        calibration_artifact=fake,
        summary_line="Fixture snapshot for test.",
        rag_evidence=rag,
        structured_slots=[
            {"slot_id": "intent.one_line", "text": "Explain macro quadrant.", "evidence_index": 0}
        ],
        lens_id=None,
        route_confidence=None,
        track="internal_lab",
        gating="advisory",
        hypothesis_label=None,
    )
    schema = json.loads(
        (ROOT / "docs/final/schemas/semantic_rag_bridge_insight_bundle_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.validate(instance=bundle, schema=schema)
    assert bundle["calibration_reference"]["artifact_path_rel"]
