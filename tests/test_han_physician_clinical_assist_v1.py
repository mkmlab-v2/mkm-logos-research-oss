"""Han physician turn + Athena 100pt pipeline smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.l0_red_flag_router_v1 import keyword_hits_from_text, load_template

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_TURN = ROOT / "reports" / "park_geumja_han_physician_assist_turn_v1.latest.json"
SCHEMA_TURN = ROOT / "docs" / "final" / "schemas" / "han_physician_clinical_assist_turn_v1.schema.json"
SCHEMA_100 = ROOT / "docs" / "final" / "schemas" / "athena_100_point_report_v1.schema.json"


@pytest.mark.skipif(not SAMPLE_TURN.is_file(), reason="sample turn missing")
def test_sample_turn_matches_schema() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    doc = json.loads(SAMPLE_TURN.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_TURN.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)


@pytest.mark.skipif(not SAMPLE_TURN.is_file(), reason="sample turn missing")
def test_render_athena_100pt_from_sample_turn() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    out = ROOT / "reports" / "_pytest_park_geumja_athena_100pt_v1.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "render_athena_100pt_from_han_turn_v1.py"),
            "--han-turn-json",
            str(SAMPLE_TURN),
            "--validate-schema",
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["schema"] == "athena_100_point_report_v1"
    schema = json.loads(SCHEMA_100.read_text(encoding="utf-8"))
    jsonschema.validate(instance=report, schema=schema)


@pytest.mark.skipif(
    not (ROOT / "reports" / "park_geumja_patient_care_bundle_latest.json").is_file(),
    reason="park_geumja bundle missing",
)
def test_build_han_turn_from_park_geumja_bundle() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_han_physician_clinical_assist_turn_v1.py"),
            "--slug",
            "park_geumja",
            "--validate-schema",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    built = ROOT / "reports" / "park_geumja_han_physician_assist_turn_v1.json"
    assert built.is_file()
    doc = json.loads(built.read_text(encoding="utf-8"))
    assert doc["schema"] == "han_physician_clinical_assist_turn_v1"


@pytest.mark.skipif(
    not (ROOT / "reports" / "lee_bomi_patient_care_bundle_latest.json").is_file(),
    reason="lee_bomi bundle missing",
)
def test_build_han_turn_from_lee_bomi_bundle() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_han_physician_clinical_assist_turn_v1.py"),
            "--slug",
            "lee_bomi",
            "--validate-schema",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    built = ROOT / "reports" / "lee_bomi_han_physician_assist_turn_v1.json"
    assert built.is_file()
    doc = json.loads(built.read_text(encoding="utf-8"))
    assert doc["schema"] == "han_physician_clinical_assist_turn_v1"
    assert doc.get("ref_token") == "LEE-BOMI-2026-001"
    assert doc.get("cohort_id") == "postpartum_2wk"
    layers = doc.get("layers") or {}
    ex = layers.get("executive_summary") or {}
    bullets = " ".join(ex.get("bullets_ko") or [])
    assert "taeeum" in bullets
    l0 = layers.get("L0_clinical_safety") or {}
    excerpt = str(l0.get("soap_assessment_excerpt") or "")
    assert "태음" in excerpt
    assert l0.get("l0_router_triggered") is False
    assert "순환" in str(layers.get("L1_hemodynamics_sleep") or "")
    assert "작열" in str(layers.get("L2_thermal_hydration") or "") or "차고" in str(layers.get("L2_thermal_hydration") or "")


def test_kampo_bench_crosscut_fixture_shape() -> None:
    path = ROOT / "docs/final/artifacts/fixtures/kampo_bench_eval_crosscut_v1.example.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["schema"] == "kampo_bench_eval_crosscut_v1"
    assert doc.get("send_gate") == "HOLD"
    assert len(doc.get("dimensions") or []) >= 6


def test_lee_bomi_l0_snippet_negative_no_trigger() -> None:
    snippet_path = ROOT / "tests/fixtures/lee_bomi_l0_intake_snippet_v1.example.json"
    snippet = json.loads(snippet_path.read_text(encoding="utf-8"))
    digest = str(snippet.get("subjective_digest") or "")
    template = load_template()
    hits = keyword_hits_from_text(digest, template)
    assert hits == []
