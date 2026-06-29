# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load_mod():
    path = _ROOT / "scripts/universal_multi_res_router_v1.py"
    spec = importlib.util.spec_from_file_location("universal_multi_res_router_v1", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_schema_low_res_sasang():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (_ROOT / "docs/final/schemas/universal_multi_res_router_v1.schema.json").read_text(encoding="utf-8")
    )
    mod = _load_mod()
    doc = mod.route_query(
        "사상 stress 계산 run_lens_sasang exit 0",
        infrastructure_mode="headless_ci",
        generated_at_utc="2026-06-29T14:00:00Z",
    )
    jsonschema.Draft7Validator(schema).validate(doc)
    assert doc["resolution_tier"] == "low_res"
    assert doc["epistemic_grade"] == "FACT"
    assert doc["domain_tag"] == "sasang"
    assert doc["inference_adapter"]["provider"] == "keyword_heuristics"
    assert doc["inference_adapter"]["fallback_triggered"] is True
    assert doc["send_gate"] == "HOLD"
    assert doc["commercial_gateway_hooks"]["metering_enabled"] is False
    assert doc["routing_overlay_policy"]["mode"] == "routing_hints_only"


def test_hold_gate_forbidden():
    mod = _load_mod()
    doc = mod.route_query(
        "Track A live trading 승격 start_live_trading",
        infrastructure_mode="headless_ci",
        generated_at_utc="2026-06-29T14:00:01Z",
    )
    assert doc["resolution_tier"] == "hold_gate"
    assert doc["epistemic_grade"] == "FORBIDDEN"
    assert "live_trading_trigger" in doc["forbidden_hits"]
    assert doc["governance_override"]["human_review_required"] is True


def test_high_res_sasang_inventory():
    mod = _load_mod()
    doc = mod.route_query(
        "사상 908 자산 전수조사 기대 vs 팩트 대조표 학파 충돌",
        infrastructure_mode="cloud_vps_api",
        generated_at_utc="2026-06-29T14:00:02Z",
    )
    assert doc["resolution_tier"] == "high_res"
    assert doc["required_ltm_depth"] >= 0.45
    assert doc["domain_plugin"]["plugin_id"] == "sasang_context_v1"
    assert "sasang_expectation_vs_fact_matrix_v1.md" in doc["domain_plugin"]["agent_read_order"][0]


def test_cli_exit_zero():
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/universal_multi_res_router_v1.py"),
            "--query",
            "사상 persona grid 빌드",
            "--infrastructure-mode",
            "headless_ci",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    out = _ROOT / "docs/final/artifacts/universal_multi_res_router_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "universal_multi_res_router_v1"
    assert "plugin_registry_ref" in doc


def test_shallow_fixture_uses_ollama_adapter(monkeypatch):
    mod = _load_mod()
    fixture = _ROOT / "docs/final/schemas/ollama_shallow_router_output_v1.example.json"
    shallow = mod._load_shallow_json(fixture)
    assert shallow is not None
    doc = mod.route_query(
        "generic ops query",
        shallow=shallow,
        infrastructure_mode="headless_ci",
        generated_at_utc="2026-06-29T15:00:00Z",
    )
    assert doc["inference_adapter"]["provider"] == "ollama"
    assert doc["inference_adapter"]["fallback_triggered"] is False
    assert doc["inference_adapter"]["shallow_router_schema_compat"] == "ollama_shallow_router_output_v1"
    assert doc["domain_tag"] == "logos"
    assert doc["shallow_router_compat"]["domain_tag"] == "logos"


def test_handoff_compat_normalizes_to_shallow():
    mod = _load_mod()
    handoff_path = _ROOT / "reports/ollama_shallow_router_handoff_v1_latest.json"
    if not handoff_path.is_file():
        pytest.skip("handoff artifact missing")
    shallow = mod._load_shallow_json(handoff_path)
    assert shallow is not None
    assert shallow["schema"] == "ollama_shallow_router_output_v1"
    assert shallow["domain_tag"] == "logos"


def test_auto_resolve_shallow_local_pc(monkeypatch):
    mod = _load_mod()
    monkeypatch.setattr(mod, "ollama_reachable", lambda *a, **k: False)
    shallow, ref = mod.resolve_shallow_packet(None, infrastructure_mode="local_pc")
    if shallow is None:
        pytest.skip("no shallow auto-candidate on disk")
    assert ref is not None
    doc = mod.route_query(
        "사상 stress 계산",
        shallow=shallow,
        shallow_artifact_ref=ref,
        infrastructure_mode="local_pc",
        generated_at_utc="2026-06-29T15:00:01Z",
    )
    assert doc["inference_adapter"]["provider"] == "ollama"
    assert doc["inference_adapter"]["fallback_triggered"] is False


def test_headless_ci_skips_auto_shallow():
    mod = _load_mod()
    shallow, ref = mod.resolve_shallow_packet(None, infrastructure_mode="headless_ci")
    assert shallow is None
    assert ref is None
