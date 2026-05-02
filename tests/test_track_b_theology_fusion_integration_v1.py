# @MKM12-METADATA
# Type: Logic
# Purpose: Track B theology baseline ↔ independent lens fusion stub wiring regression.
# Keywords: logos, theology, fusion_stub, track_b, integration

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_THEOLOGY = _ROOT / "docs" / "final" / "artifacts" / "LOGOS_MKM_THEOLOGY_BASELINE_V1.json"
_FUSION_RUNNER = _ROOT / "scripts" / "report_independent_lens_fusion_stub_v0.py"


def _minimal_lens(schema: str, lens_id: str, direction: float, conf: float) -> dict:
    return {
        "schema": schema,
        "version": "0.1.0",
        "lens_id": lens_id,
        "engine_id": "independent_lens_v0",
        "ts_utc": "2026-05-02T12:00:00Z",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "scores": {"direction_score": direction, "confidence": conf},
    }


def test_theology_baseline_declares_fusion_runner_path() -> None:
    doc = json.loads(_THEOLOGY.read_text(encoding="utf-8"))
    dr = doc.get("track_b_deep_research_interpretation_policy") or {}
    runner = (dr.get("fusion_stub_cross_reference") or {}).get("runner", "")
    assert runner == "scripts/report_independent_lens_fusion_stub_v0.py"


def test_fusion_stub_with_fixture_lenses_wires_logos_verse_ids(tmp_path: Path) -> None:
    mye = tmp_path / "myeongni.json"
    sas = tmp_path / "sasang.json"
    logos = tmp_path / "logos.json"
    mye.write_text(
        json.dumps(_minimal_lens("myeongni_independent_lens_v0", "myeongni", 0.5, 0.6), ensure_ascii=False),
        encoding="utf-8",
    )
    sas.write_text(
        json.dumps(_minimal_lens("sasang_independent_lens_v0", "sasang", -0.2, 0.5), ensure_ascii=False),
        encoding="utf-8",
    )
    logos_doc = _minimal_lens("logos_independent_lens_v0", "logos", -0.3, 0.4)
    logos_doc["evidence_refs"] = [
        {"verse_id": "INT-001", "hash_tagged_snippet": "[#INT-001]"},
        {"verse_id": "INT-002", "hash_tagged_snippet": "[#INT-002]"},
    ]
    logos.write_text(json.dumps(logos_doc, ensure_ascii=False), encoding="utf-8")

    out = tmp_path / "fusion.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_FUSION_RUNNER),
            "--myeongni",
            str(mye),
            "--sasang",
            str(sas),
            "--logos",
            str(logos),
            "--no-market-sasang",
            "--output",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    fusion = json.loads(out.read_text(encoding="utf-8"))
    csum = fusion.get("conflict_summary") or {}
    ids = csum.get("logos_evidence_verse_ids") or []
    assert ids == ["INT-001", "INT-002"]
    assert fusion.get("hypothesis_tier") == "B"
    assert fusion.get("boundary_ack") is True


def test_policy_readiness_still_ok_after_theology_baseline() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "report_logos_track_b_policy_readiness_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    latest = _ROOT / "docs" / "final" / "artifacts" / "logos_track_b_policy_readiness_v1_latest.json"
    doc = json.loads(latest.read_text(encoding="utf-8"))
    assert doc.get("overall_ok") is True
    assert doc.get("checks", {}).get("theology_jsonschema") == "ok"
