# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def test_registry_build_exit_zero():
    r = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/build_universal_multi_res_plugin_registry_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr


def test_registry_schema_and_lanes():
    jsonschema = pytest.importorskip("jsonschema")
    test_registry_build_exit_zero()
    schema = json.loads(
        (_ROOT / "docs/final/schemas/universal_multi_res_plugin_registry_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    doc = json.loads(
        (_ROOT / "docs/final/artifacts/universal_multi_res_plugin_registry_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.Draft7Validator(schema).validate(doc)
    lanes = set(doc["plugins"].keys())
    assert {"sasang", "myeongni", "logos", "science"}.issubset(lanes)
    assert doc["plugins"]["science"]["u3_tier"] == "stub"
    assert doc["plugins"]["myeongni"]["u3_tier"] == "lite"
    assert doc["plugins"]["logos"]["u3_tier"] == "lite_plus"
    assert "logos_context_inventory_v1_latest.json" in (
        doc["plugins"]["logos"].get("inventory_artifact_ref") or ""
    )


def test_router_myeongni_logos_science_plugins():
    test_registry_build_exit_zero()
    path = _ROOT / "scripts/universal_multi_res_router_v1.py"
    spec = importlib.util.spec_from_file_location("umr_reload", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.DOMAIN_PLUGINS = mod._load_plugin_registry()

    myeongni = mod.route_query(
        "명리 학파 충돌 표면 기대 vs 팩트",
        infrastructure_mode="headless_ci",
        generated_at_utc="2026-06-29T16:00:00Z",
    )
    assert myeongni["domain_tag"] == "myeongni"
    assert myeongni["domain_plugin"]["plugin_id"] == "myeongni_lens_v1"
    assert "myeongni_expectation_vs_fact_matrix_v1_lite.md" in myeongni["domain_plugin"]["agent_read_order"][0]

    logos = mod.route_query(
        "Logos GraphRAG gold spot check",
        infrastructure_mode="headless_ci",
        generated_at_utc="2026-06-29T16:00:01Z",
    )
    assert logos["domain_tag"] == "logos"
    assert logos["domain_plugin"]["plugin_id"] == "logos_lens_v1"

    science = mod.route_query(
        "UFT geumhwa_index 계산 exit 0",
        infrastructure_mode="headless_ci",
        generated_at_utc="2026-06-29T16:00:02Z",
    )
    assert science["domain_tag"] == "science"
    assert science["domain_plugin"]["plugin_id"] == "uft_core_v1_stub"
    assert science["plugin_registry_ref"].endswith("universal_multi_res_plugin_registry_v1_latest.json")
