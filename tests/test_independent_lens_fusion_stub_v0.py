# @MKM12-METADATA
# Type: Logic
# Purpose: Regression for independent lens fusion stub v0 reporter.
# Keywords: fusion_stub, independent_lens, comparison

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


_ROOT = Path(__file__).resolve().parents[1]
_RUNNER = _ROOT / "scripts" / "report_independent_lens_fusion_stub_v0.py"
_CONTRACT = _ROOT / "docs" / "final" / "artifacts" / "INDEPENDENT_LENS_FUSION_STUB_V0_CONTRACT.json"
_SCHEMA = _ROOT / "docs" / "final" / "schemas" / "independent_lens_fusion_stub_v0.schema.json"


def test_contract_file_exists() -> None:
    assert _CONTRACT.is_file()
    doc = json.loads(_CONTRACT.read_text(encoding="utf-8"))
    assert doc.get("artifact_schema") == "independent_lens_fusion_stub_v0"
    assert doc.get("runner") == "scripts/report_independent_lens_fusion_stub_v0.py"
    assert doc.get("artifact_json_schema") == "docs/final/schemas/independent_lens_fusion_stub_v0.schema.json"
    assert _SCHEMA.is_file()


def test_json_schema_is_valid_draft07() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(schema)


def test_runner_emits_fusion_summary(tmp_path: Path) -> None:
    out = tmp_path / "fusion.json"
    cp = subprocess.run(
        [sys.executable, str(_RUNNER), "--output", str(out)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "independent_lens_fusion_stub_v0"
    assert doc.get("hypothesis_tier") == "B"
    assert doc.get("boundary_ack") is True
    inputs = doc.get("inputs") or []
    assert len(inputs) in (3, 4, 5)
    cs = doc.get("consensus") or {}
    assert 0.0 <= float(cs.get("agreement_rate", 0.0)) <= 1.0
    assert -1.0 <= float(cs.get("consensus_score", 0.0)) <= 1.0
    assert doc.get("version") == "0.5.0"
    assert isinstance(doc.get("sidecar_rails"), list)
    assert len(doc.get("sidecar_rails") or []) == 3
    assert isinstance(doc.get("consensus_effective"), dict)
    assert isinstance(doc.get("headline_gating"), dict)
    csum = doc.get("conflict_summary") or {}
    assert isinstance(csum.get("conflict_narrative_guarded"), str)
    assert len(csum.get("conflict_narrative_guarded", "")) >= 10
    assert isinstance(csum.get("minority_lens_ids"), list)
    assert isinstance(csum.get("logos_evidence_verse_ids"), list)
    assert csum.get("narrative_policy")

    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)


def test_runner_legacy_three_lenses_no_market_sasang(tmp_path: Path) -> None:
    out = tmp_path / "fusion3.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_RUNNER),
            "--no-market-sasang",
            "--no-market-myeongni",
            "--output",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert len(doc.get("inputs") or []) == 3
    assert doc.get("version") == "0.5.0"
    assert isinstance(doc.get("sidecar_rails"), list)
    assert len(doc.get("sidecar_rails") or []) == 3
    assert isinstance(doc.get("consensus_effective"), dict)
    assert isinstance(doc.get("headline_gating"), dict)


def test_v05_demote_on_shock_sidecar_bear_fixture(tmp_path: Path) -> None:
    from scripts.report_independent_lens_fusion_stub_v0 import build_fusion_stub_document

    art = tmp_path / "docs" / "final" / "artifacts"
    art.mkdir(parents=True)

    def _w(name: str, obj: dict) -> Path:
        p = art / name
        p.write_text(json.dumps(obj), encoding="utf-8")
        return p

    myeongni = _w(
        "myeongni_independent_lens_latest.json",
        {
            "schema": "myeongni_independent_lens_v0",
            "lens_id": "myeongni",
            "ts_utc": "2026-06-08T00:15:20Z",
            "scores": {"direction_score": 0.08, "confidence": 0.68552},
        },
    )
    sasang = _w(
        "sasang_independent_lens_latest.json",
        {
            "schema": "sasang_independent_lens_v0",
            "lens_id": "sasang",
            "ts_utc": "2026-06-08T00:15:20Z",
            "scores": {"direction_score": 0.17, "confidence": 0.7115},
        },
    )
    logos = _w(
        "logos_independent_lens_latest.json",
        {
            "schema": "logos_independent_lens_v0",
            "lens_id": "logos",
            "ts_utc": "2026-06-08T00:15:20Z",
            "scores": {"direction_score": -0.323333, "confidence": 0.2},
        },
    )
    market_sasang = _w(
        "market_sasang_lens_latest.json",
        {
            "schema": "market_sasang_lens_v1",
            "ts_utc": "2026-06-07T23:25:15Z",
            "fusion_bridge": {"score_hint": 0.17, "direction_hint": "bull"},
            "uncertainty": {"composite_uncertainty": 0.67235122},
            "veto": {"force_hold": True, "reason_codes": ["HIGH_ENTROPY_SOFTMAX"]},
        },
    )
    market_myeongni = _w(
        "market_myeongni_lens_latest.json",
        {
            "schema": "market_myeongni_lens_v1",
            "ts_utc": "2026-06-07T23:25:15Z",
            "direction_sign": "neutral",
            "scores": {"direction_score": 0.0536, "confidence": 0.603258},
            "overlay": {
                "base_direction_score": 0.08,
                "base_confidence": 0.68552,
                "upstream_lens_id": "myeongni",
                "applied": {},
            },
        },
    )
    news = _w(
        "news_independent_lens_latest.json",
        {
            "schema": "news_independent_lens_v0",
            "lens_id": "news",
            "ts_utc": "2026-06-07T23:00:24Z",
            "scores": {"direction_score": -0.07384, "confidence": 0.6},
        },
    )
    macro = _w(
        "macro_independent_lens_latest.json",
        {
            "schema": "macro_independent_lens_v0",
            "lens_id": "macro",
            "ts_utc": "2026-06-07T23:00:20Z",
            "scores": {"direction_score": -0.037106, "confidence": 0.6},
        },
    )
    overnight = _w(
        "global_market_overnight_signals_v1_latest.json",
        {
            "schema": "global_market_overnight_signals_v1",
            "generated_at_utc": "2026-06-07T23:00:12Z",
            "composite_tilt": "risk_off_overnight",
            "indices": [{"change_pct": -4.18}],
        },
    )

    doc = build_fusion_stub_document(
        myeongni=myeongni,
        sasang=sasang,
        logos=logos,
        market_sasang=market_sasang,
        market_myeongni=market_myeongni,
        news=news,
        macro=macro,
        overnight=overnight,
        include_market_sasang=True,
        include_market_myeongni=True,
    )

    assert doc["version"] == "0.5.0"
    assert doc["consensus"]["consensus_sign"] == "bull"
    assert doc["demote_active"] is True
    assert doc["headline_gating"]["non_gating"] is True
    assert doc["headline_gating"]["headline_sign"] == "bear"
    assert doc["consensus_effective"]["consensus_sign"] == "bear"
    assert any("R1_conflict_count_ge_2" in t for t in doc["demote_trace"])


def test_resolve_fusion_headline_v1_prefers_headline_gating() -> None:
    from scripts.report_independent_lens_fusion_stub_v0 import resolve_fusion_headline_v1

    hl = resolve_fusion_headline_v1(
        {
            "consensus": {"consensus_sign": "bull"},
            "consensus_effective": {"consensus_sign": "bear"},
            "headline_gating": {
                "headline_sign": "bear",
                "non_gating": True,
                "headline_source": "consensus_effective",
            },
            "demote_active": True,
        }
    )
    assert hl["headline_sign"] == "bear"
    assert hl["raw_consensus_sign"] == "bull"
    assert hl["non_gating"] is True
