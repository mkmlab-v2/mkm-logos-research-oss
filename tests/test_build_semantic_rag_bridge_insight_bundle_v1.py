"""Smoke tests for build_semantic_rag_bridge_insight_bundle_v1 CLI builder."""

from __future__ import annotations

import json
import subprocess
import sys
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


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_philosophy_pilot_json_merges_blocks(tmp_path: Path) -> None:
    from scripts.build_semantic_rag_bridge_insight_bundle_v1 import (
        build_bundle,
        rag_evidence_from_philosophy_pilot_v1,
    )

    pilot = {
        "schema": "philosophy_lane_rag_pilot_v1",
        "blocks": [
            {
                "source_rail": "fixture_rail",
                "summary": "Summary line.",
                "detail": "Detail line.",
                "evidence_path": "docs/final/artifacts/example.sqlite",
            }
        ],
    }
    rows = rag_evidence_from_philosophy_pilot_v1(pilot)
    assert len(rows) == 1
    assert "Summary" in rows[0]["snippet"]

    bundle = build_bundle(
        calibration_kind="none",
        calibration_artifact=None,
        summary_line=None,
        rag_evidence=[],
        structured_slots=None,
        lens_id=None,
        route_confidence=None,
        track="B-track",
        gating="NON_GATING",
        hypothesis_label="[HYPO]",
    )
    merged = (bundle["rag_evidence"] + rows)[:24]
    bundle2 = build_bundle(
        calibration_kind="none",
        calibration_artifact=None,
        summary_line=None,
        rag_evidence=merged,
        structured_slots=None,
        lens_id=None,
        route_confidence=None,
        track="B-track",
        gating="NON_GATING",
        hypothesis_label="[HYPO]",
    )
    schema = json.loads(
        (ROOT / "docs/final/schemas/semantic_rag_bridge_insight_bundle_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.validate(instance=bundle2, schema=schema)
    assert len(bundle2["rag_evidence"]) == 1

    pilot_path = tmp_path / "pilot.json"
    pilot_path.write_text(json.dumps(pilot), encoding="utf-8")
    out_path = tmp_path / "bridge.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_semantic_rag_bridge_insight_bundle_v1.py"),
            "--calibration-kind",
            "none",
            "--philosophy-pilot-json",
            str(pilot_path),
            "--out",
            str(out_path),
            "--strict",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(written["rag_evidence"]) == 1
    assert written["rag_evidence"][0]["source_id"].startswith("philosophy_lane_rag_pilot:")


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_rag_evidence_from_premium_example_json() -> None:
    from scripts.build_semantic_rag_bridge_insight_bundle_v1 import (
        build_bundle,
        rag_evidence_from_premium_multilens_report_v1,
    )

    ex_path = ROOT / "docs/final/schemas/premium_btrack_multilens_report_v1.example.json"
    doc = json.loads(ex_path.read_text(encoding="utf-8"))
    rows = rag_evidence_from_premium_multilens_report_v1(doc)
    assert len(rows) == 3
    assert all(r["source_id"].startswith("premium_ml:") for r in rows)
    assert rows[0]["confidence_band"] in ("A", "B", "C")

    bundle = build_bundle(
        calibration_kind="none",
        calibration_artifact=None,
        summary_line="Premium fixture smoke.",
        rag_evidence=rows,
        structured_slots=[{"slot_id": "intent.stub", "text": "From premium example.", "evidence_index": 0}],
        lens_id=None,
        route_confidence=None,
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


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_cli_premium_multilens_flag_writes_bundle(tmp_path: Path) -> None:
    ex_path = ROOT / "docs/final/schemas/premium_btrack_multilens_report_v1.example.json"
    out_path = tmp_path / "bridge_from_premium.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_semantic_rag_bridge_insight_bundle_v1.py"),
            "--calibration-kind",
            "none",
            "--summary-line",
            "premium example fixture",
            "--premium-multilens-report-json",
            str(ex_path),
            "--out",
            str(out_path),
            "--strict",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(written["rag_evidence"]) == 3
    assert written["version"] == "1.0.2"
