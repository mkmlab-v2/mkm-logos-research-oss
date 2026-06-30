"""JEMA OS domain plugin registry v2 — slot standardization + pin isolation."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_jema_os_domain_plugin_registry_v2.py"
CHECK = ROOT / "scripts/check_jema_os_domain_plugin_registry_v2.py"
REGISTRY = ROOT / "docs/final/artifacts/jema_os_domain_plugin_registry_v2_latest.json"
SCHEMA = ROOT / "docs/final/schemas/jema_os_domain_plugin_registry_v2.schema.json"
PUBLIC = ROOT / "projects/mkm/mkm-life/public/data/jema_os_domain_plugin_registry_v2.json"


def test_build_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(BUILD)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_registry_schema_slots_and_isolation():
    jsonschema = pytest.importorskip("jsonschema")
    test_build_exit_zero()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    slots = set(doc["slots"].keys())
    assert {"logos", "sasang", "myeongni", "enterprise_herbs_formulas", "lens_audio", "design_surface"}.issubset(slots)
    assert doc["slots"]["logos"]["knowledge_pin"]["min_line_count_floor"] == 290_000
    assert doc["slots"]["enterprise_herbs_formulas"]["knowledge_pin"]["min_line_count_floor"] == 8
    assert doc["slots"]["myeongni"]["spec_gap_intake_lane"] == "myeongri"
    assert doc["live_llm_on_surface"] is False
    assert doc["send_gate"] == "HOLD"
    assert PUBLIC.is_file()


def test_check_exit_zero():
    test_build_exit_zero()
    proc = subprocess.run(
        [sys.executable, str(CHECK)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads(
        (ROOT / "reports/jema_os_domain_plugin_registry_v2_check_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["ok"] is True
    assert report["pin_isolation"]["overlap_count"] == 0


def test_umr_router_resolves_v2_slot_overlay():
    test_build_exit_zero()
    path = ROOT / "scripts/universal_multi_res_router_v1.py"
    spec = importlib.util.spec_from_file_location("umr_v2_overlay", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.DOMAIN_PLUGINS = mod._load_plugin_registry()

    logos = mod.route_query(
        "Logos GraphRAG gold spot check",
        infrastructure_mode="headless_ci",
        generated_at_utc="2026-06-30T03:00:00Z",
    )
    assert logos["domain_tag"] == "logos"
    overlay = logos.get("domain_plugin_slot_v2")
    assert overlay and overlay["slot_id"] == "logos"
    assert overlay["has_knowledge_pin"] is True
    assert overlay["knowledge_pin_floor"] == 290_000
    assert logos["jema_os_plugin_registry_v2_ref"].endswith(
        "jema_os_domain_plugin_registry_v2_latest.json"
    )

    enterprise = mod.route_query(
        "한방 본초 방제 탕액 herbs formulas PoC",
        infrastructure_mode="headless_ci",
        generated_at_utc="2026-06-30T03:00:01Z",
    )
    assert enterprise["domain_tag"] == "enterprise_herbs_formulas"
    assert enterprise["domain_plugin"]["plugin_id"] == "enterprise_herbs_formulas_v1"
    ent_overlay = enterprise.get("domain_plugin_slot_v2")
    assert ent_overlay and ent_overlay["slot_id"] == "enterprise_herbs_formulas"
    assert ent_overlay["spec_gap_intent_chip"] == "clinician"
