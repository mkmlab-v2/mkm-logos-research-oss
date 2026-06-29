"""Registry → clinic MVP capture backfill."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.import_clinic_mvp_from_patient_registry_v1 import (
    build_capture_from_intake,
    map_korean_sasang_label,
    observation_proxies_from_intake,
    run_import,
)
from scripts.clinic_constitution_mvp_ledger_v1 import validate_clinic_capture_record

ROOT = Path(__file__).resolve().parent.parent


def test_map_korean_sasang_labels() -> None:
    assert map_korean_sasang_label("소음인 추정(확실치 않음)")[0] == "soeum"
    assert map_korean_sasang_label("소양인 추정(확실치 않음)")[0] == "soyang"
    assert map_korean_sasang_label("미입력(영유아·관찰 부족)")[0] == "uncertain"


def test_soyoung_intake_builds_valid_capture() -> None:
    intake_path = ROOT / "reports/soyoung_choi_intake_fusion_v1.json"
    doc = json.loads(intake_path.read_text(encoding="utf-8"))
    record = build_capture_from_intake(
        doc, slug="soyoung_choi", physician_from_estimate=False
    )
    assert record["encounter"]["ref_token"] == "SOYOUNG-G3-2026-001"
    assert record["ai_hypothesis"]["constitution"] == "soeum"
    assert record["physician_constitution"]["label"] == "withheld"
    assert validate_clinic_capture_record(record) == []


def test_proxies_in_range() -> None:
    doc = json.loads(
        (ROOT / "reports/park_geumja_intake_fusion_v1.json").read_text(encoding="utf-8")
    )
    proxies = observation_proxies_from_intake(doc["intake"])
    for v in proxies.values():
        assert 0.0 <= v <= 1.0
    assert proxies["cold_heat_lean"] > 0.5


def test_dry_run_skips_operator_and_family() -> None:
    report = run_import(
        ROOT,
        dry_run=True,
        skip_existing=False,
        physician_from_estimate=False,
        slugs=None,
    )
    assert report["n_appended"] >= 5
    assert "COMMANDER" not in report["ref_tokens_appended"]
    assert "FAMILY" not in "".join(report["ref_tokens_appended"])
