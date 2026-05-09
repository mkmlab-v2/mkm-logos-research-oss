"""Compression token API stub (FastAPI)."""

from __future__ import annotations

import base64
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts.compression_token_api_stub import app

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]
OPENAPI_STUB = ROOT / "docs" / "final" / "openapi_token_compression_stub_v1.yaml"
PARITY_DEBUG_OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "token_api_parity_debug_latest.json"


def _write_parity_debug(payload: dict, details: list[dict]) -> None:
    PARITY_DEBUG_OUT.parent.mkdir(parents=True, exist_ok=True)
    git_sha = os.getenv("GITHUB_SHA", "").strip()
    if not git_sha:
        try:
            git_sha = (
                subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(ROOT),
                    check=True,
                    capture_output=True,
                    text=True,
                )
                .stdout.strip()
            )
        except Exception:
            git_sha = ""
    by_example: dict[str, int] = {}
    by_reason: dict[str, int] = {}
    for d in details:
        ex = str(d.get("example") or d.get("payload", {}).get("example_name") or "unknown")
        rs = str(d.get("reason") or "unknown")
        by_example[ex] = by_example.get(ex, 0) + 1
        by_reason[rs] = by_reason.get(rs, 0) + 1
    top_reason = None
    if by_reason:
        reason, count = max(by_reason.items(), key=lambda kv: kv[1])
        top_reason = {"reason": reason, "count": count}
    top_example = None
    if by_example:
        example, count = max(by_example.items(), key=lambda kv: kv[1])
        top_example = {"example": example, "count": count}
    doc = {
        "schema": "token_api_parity_debug_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha or None,
        "workflow_run_id": os.getenv("GITHUB_RUN_ID"),
        "payload": payload,
        "summary": {
            "mismatch_count": len(details),
            "by_example": by_example,
            "by_reason": by_reason,
            "top_example": top_example,
            "top_reason": top_reason,
        },
        "details": details,
    }
    PARITY_DEBUG_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j.get("status") == "ok"
    assert j.get("api_contract_version") == "1.0.0"
    assert j.get("tier_policy", {}).get("enterprise_keys_configured") is False
    assert "kpi_snapshot" in j
    assert "ultra_literal_global_token_saving_rate" in j.get("kpi_snapshot", {})


def test_freemium_public_tier_when_enterprise_keys_configured(monkeypatch):
    monkeypatch.setenv("COMPRESSION_API_ENTERPRISE_KEYS", "secret-enterprise-key")
    from scripts.compression_token_api_stub import _enterprise_key_list, _resolve_tier

    assert "secret-enterprise-key" in _enterprise_key_list()

    class Req:
        def __init__(self, headers: dict[str, str]) -> None:
            self.headers = headers

    assert _resolve_tier(Req({"x-api-key": "wrong"})) == "public"
    assert _resolve_tier(Req({"x-api-key": "secret-enterprise-key"})) == "enterprise"


def test_public_tier_can_use_ultra_literal_runner_hint(monkeypatch):
    monkeypatch.setenv("COMPRESSION_API_ENTERPRISE_KEYS", "secret-enterprise-key")
    r = client.post(
        "/v1/compress",
        json={
            "text": "public precision-first test 텍스트",
            "eval_context": {"runner_hint": "ultra_literal"},
        },
        headers={"x-api-key": "wrong"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("integrity_flags", {}).get("tier") == "public"
    assert data.get("integrity_flags", {}).get("sla_track") == "ultra_literal"
    assert data.get("integrity_flags", {}).get("metrics_mode") == "ultra_literal_kpi_estimate"
    metrics = data.get("compression_metrics") or {}
    assert 0.0 <= float(metrics.get("savings_ratio", -1.0)) <= 1.0


def test_public_tier_bulkhead_never_calls_live_eval_even_when_requested(monkeypatch):
    """Track B (public tier): live evaluate_report path must not run (A/B bulkhead)."""
    monkeypatch.setenv("COMPRESSION_API_ENTERPRISE_KEYS", "secret-enterprise-key")
    monkeypatch.setenv("COMPRESSION_API_LIVE_EVAL_MIN_TOKENS", "0")
    from scripts import compression_token_api_stub as stub

    stub._live_eval_min_tokens.cache_clear()

    def _live_eval_must_not_run(*_args, **_kwargs):
        raise AssertionError("public tier must not invoke _live_eval_metrics / live evaluate_report")

    monkeypatch.setattr(stub, "_live_eval_metrics", _live_eval_must_not_run)

    payload = {
        "text": "bulkhead public tier " * 30,
        "eval_context": {
            "hydrate_metrics": True,
            "hydrate_live_eval": True,
            "runner_hint": "active_default",
        },
    }
    r = client.post("/v1/compress", json=payload, headers={"x-api-key": "wrong"})
    assert r.status_code == 200
    d = r.json()
    flags = d.get("integrity_flags") or {}
    assert flags.get("tier") == "public"
    assert flags.get("hydrate_live_eval_suppressed") is True
    assert flags.get("hydrate_live_eval_suppressed_reason") == "public_tier_use_enterprise_key"
    assert flags.get("hydration_metrics_source") != "live_evaluate_report"
    assert flags.get("metrics_mode") in {"literal_kpi_estimate", "ultra_literal_kpi_estimate"}


def test_enterprise_fallback_trigger_suppresses_live_eval(monkeypatch, tmp_path):
    profile = tmp_path / "fallback_profile.json"
    profile.write_text(
        json.dumps(
            {
                "schema": "fallback_trigger_threshold_profile_v1",
                "signals": {
                    "oov_ratio_threshold": 0.01,
                    "typo_ratio_threshold": 0.01,
                    "input_tokens_threshold": 10,
                    "unknown_token_rate_threshold": 0.01,
                    "detected_noise_mode_threshold": 0.01,
                },
                "trigger_logic": {"mode": "any_of"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("COMPRESSION_API_FALLBACK_PROFILE_PATH", str(profile))
    monkeypatch.setenv("COMPRESSION_API_LIVE_EVAL_MIN_TOKENS", "0")
    from scripts import compression_token_api_stub as stub

    stub._live_eval_min_tokens.cache_clear()
    stub._fallback_profile_doc.cache_clear()

    def _live_eval_must_not_run(*_args, **_kwargs):
        raise AssertionError("fallback-triggered request must suppress live eval")

    monkeypatch.setattr(stub, "_live_eval_metrics", _live_eval_must_not_run)
    r = client.post(
        "/v1/compress",
        json={
            "text": "### noisy $$$ payload ??? with symbols !!!",
            "eval_context": {
                "hydrate_metrics": True,
                "hydrate_live_eval": True,
            },
        },
    )
    assert r.status_code == 200
    d = r.json()
    flags = d.get("integrity_flags", {})
    assert flags.get("tier") == "enterprise"
    assert flags.get("fallback_safe_triggered") is True
    assert flags.get("hydrate_live_eval_suppressed") is True
    assert flags.get("hydrate_live_eval_suppressed_reason") == "fallback_safe_triggered"


def test_fallback_event_log_appended(monkeypatch, tmp_path):
    profile = tmp_path / "fallback_profile.json"
    profile.write_text(
        json.dumps(
            {
                "schema": "fallback_trigger_threshold_profile_v1",
                "signals": {
                    "oov_ratio_threshold": 0.01,
                    "typo_ratio_threshold": 0.01,
                    "input_tokens_threshold": 10,
                    "unknown_token_rate_threshold": 0.01,
                    "detected_noise_mode_threshold": 0.01,
                },
                "trigger_logic": {"mode": "any_of"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    event_log = tmp_path / "fallback_event_log.jsonl"
    monkeypatch.setenv("COMPRESSION_API_FALLBACK_PROFILE_PATH", str(profile))
    monkeypatch.setenv("FALLBACK_TRIGGER_EVENT_LOG_PATH", str(event_log))
    from scripts import compression_token_api_stub as stub

    stub._fallback_profile_doc.cache_clear()
    r = client.post("/v1/compress", json={"text": "### noisy $$$ payload ??? with symbols !!!"})
    assert r.status_code == 200
    d = r.json()
    flags = d.get("integrity_flags", {})
    assert flags.get("fallback_event_logged") is True
    lines = event_log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    evt = json.loads(lines[-1])
    assert evt.get("event_schema") == "fallback_trigger_event_v1"
    assert evt.get("triggered") is True


def test_compress_returns_shard():
    r = client.post("/v1/compress", json={"text": "bible test hangul 테스트"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("api_contract_version") == "1.0.0"
    assert data.get("shard_id")
    assert data.get("domain")
    assert data.get("router_only") is True
    assert "original_text" in data
    assert data.get("compression_metrics") in (None, {})
    assert data.get("integrity_flags", {}).get("metrics_mode") == "none"


def test_compress_eval_context_and_client_id_echo():
    payload = {
        "text": "trace",
        "client_request_id": "req-abc",
        "eval_context": {
            "eval_input_relative_path": "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
            "runner_hint": "active_default",
        },
        "hydration_hints": {"atom_ids": ["atom:x", "atom:y"]},
    }
    r = client.post("/v1/compress", json=payload)
    assert r.status_code == 200
    d = r.json()
    assert d["client_request_id"] == "req-abc"
    assert d["eval_context_echo"]["runner_hint"] == "active_default"
    assert d["integrity_flags"].get("hydration_atom_id_count") == 2
    assert d.get("compression_metrics") in (None, {})


def test_compress_hydrates_metrics_when_requested():
    payload = {
        "text": "compression hydration test 텍스트",
        "eval_context": {
            "hydrate_metrics": True,
            "runner_hint": "decision_lock",
        },
    }
    r = client.post("/v1/compress", json=payload)
    assert r.status_code == 200
    d = r.json()
    metrics = d.get("compression_metrics")
    if metrics:
        assert int(metrics.get("bytes_in", 0)) > 0
        assert int(metrics.get("bytes_out", -1)) >= 0
        assert int(metrics.get("token_in", 0)) >= 0
        assert int(metrics.get("token_out", 0)) >= 0
        assert 0.0 <= float(metrics.get("savings_ratio", -1)) <= 1.0
        assert d.get("integrity_flags", {}).get("hydration_metrics_source") == "decision_selected_candidate"
        assert d.get("integrity_flags", {}).get("metrics_mode") == "decision_fallback"
    else:
        assert d.get("integrity_flags", {}).get("hydration_metrics_unavailable") is True


def test_compress_prefers_live_eval_when_requested(monkeypatch):
    from scripts import compression_token_api_stub as stub

    monkeypatch.setenv("COMPRESSION_API_LIVE_EVAL_MIN_TOKENS", "0")
    stub._live_eval_min_tokens.cache_clear()
    payload = {
        "text": "live eval hydration path 성능 테스트",
        "eval_context": {
            "hydrate_metrics": True,
            "hydrate_live_eval": True,
            "runner_hint": "active_default",
        },
    }
    r = client.post("/v1/compress", json=payload)
    assert r.status_code == 200
    d = r.json()
    metrics = d.get("compression_metrics")
    if metrics:
        assert int(metrics.get("bytes_in", 0)) == len(payload["text"].encode("utf-8"))
        assert int(metrics.get("bytes_out", -1)) >= 0
        assert int(metrics.get("token_in", 0)) >= 0
        assert int(metrics.get("token_out", 0)) >= 0
        assert 0.0 <= float(metrics.get("savings_ratio", -1)) <= 1.0
        src = d.get("integrity_flags", {}).get("hydration_metrics_source")
        assert src in {"live_evaluate_report", "decision_selected_candidate"}
        mm = d.get("integrity_flags", {}).get("metrics_mode")
        assert mm in {"live", "decision_fallback"}
        assert "hydration_live_eval_elapsed_ms" in d.get("integrity_flags", {})
    else:
        assert d.get("integrity_flags", {}).get("hydration_metrics_unavailable") is True


def test_compress_emit_semantic_pointer_with_live_eval(monkeypatch):
    from scripts import compression_token_api_stub as stub

    monkeypatch.setenv("COMPRESSION_API_LIVE_EVAL_MIN_TOKENS", "0")
    stub._live_eval_min_tokens.cache_clear()
    r = client.post(
        "/v1/compress",
        json={
            "text": "emit semantic pointer live eval path " * 4,
            "eval_context": {
                "hydrate_metrics": True,
                "hydrate_live_eval": True,
                "emit_semantic_pointer": True,
            },
        },
    )
    assert r.status_code == 200
    d = r.json()
    sp = d.get("semantic_pointer")
    if d.get("integrity_flags", {}).get("hydration_metrics_source") == "live_evaluate_report":
        assert isinstance(sp, dict)
        assert sp.get("schema") == "semantic_pointer_v1"
    else:
        assert sp is None


def test_compress_reuses_live_eval_for_shadow_compare(monkeypatch):
    from scripts import compression_token_api_stub as stub

    monkeypatch.setenv("COMPRESSION_API_LIVE_EVAL_MIN_TOKENS", "0")
    stub._live_eval_min_tokens.cache_clear()
    calls = {"n": 0}

    def _fake_live_eval(text: str, *, bytes_in=None, token_in=None, emit_semantic_pointer=False):
        calls["n"] += 1
        return (
            stub.CompressionMetrics(
                bytes_in=len(text.encode("utf-8")),
                bytes_out=5,
                token_in=3,
                token_out=2,
                savings_ratio=0.33,
            ),
            1.23,
            None,
            None,
        )

    monkeypatch.setattr(stub, "_live_eval_metrics", _fake_live_eval)
    r = client.post(
        "/v1/compress",
        json={
            "text": "reuse live eval once",
            "eval_context": {
                "hydrate_metrics": True,
                "hydrate_live_eval": True,
                "hydrate_shadow_compare": True,
            },
        },
    )
    assert r.status_code == 200
    data = r.json()
    flags = data.get("integrity_flags", {})
    assert calls["n"] == 1
    assert flags.get("metrics_mode") == "live"
    assert flags.get("shadow_mode") == "enabled"
    assert flags.get("shadow_live_eval_reused_from_hydration") is True


def test_compress_skips_live_eval_for_short_input(monkeypatch):
    from scripts import compression_token_api_stub as stub

    monkeypatch.setenv("COMPRESSION_API_LIVE_EVAL_MIN_TOKENS", "999")
    stub._live_eval_min_tokens.cache_clear()
    r = client.post(
        "/v1/compress",
        json={
            "text": "short live eval skip",
            "eval_context": {
                "hydrate_metrics": True,
                "hydrate_live_eval": True,
            },
        },
    )
    assert r.status_code == 200
    data = r.json()
    flags = data.get("integrity_flags", {})
    assert flags.get("hydration_live_eval_skipped") is True
    assert flags.get("hydration_live_eval_skip_reason") == "short_input"
    assert data.get("compression_metrics") is not None


def test_expand_roundtrip_echo():
    r0 = client.post("/v1/compress", json={"text": "roundtrip"})
    p = r0.json()
    r1 = client.post("/v1/expand", json={"payload": p})
    assert r1.status_code == 200
    body = r1.json()
    assert body.get("text") == "roundtrip"
    assert body.get("api_contract_version") == "1.0.0"


def test_hybrid_codec_v0_compress_expand_roundtrip(monkeypatch):
    monkeypatch.setenv("COMPRESSION_API_USE_HYBRID_CODEC_V0", "1")
    text = "오늘 시스템이 BTCUSDT 리포트를 연구모드로 검증했다"
    r0 = client.post("/v1/compress", json={"text": text})
    assert r0.status_code == 200
    body0 = r0.json()
    flags = body0.get("integrity_flags", {})
    assert flags.get("hybrid_codec_v0_enabled") is True
    assert flags.get("hybrid_codec_v0_exact_restore_ok") is True
    assert flags.get("hybrid_codec_v0_checksum_ok") is True
    payload = flags.get("hybrid_codec_v0_payload")
    assert isinstance(payload, dict)
    assert payload.get("schema") == "hybrid_codec_v0_payload_v1"

    r1 = client.post("/v1/expand", json={"payload": {"hybrid_codec_v0_payload": payload}})
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1.get("text") == text
    assert body1.get("integrity_flags", {}).get("lossless_echo") is True


def test_hybrid_codec_v0_expand_accepts_direct_payload(monkeypatch):
    monkeypatch.setenv("COMPRESSION_API_USE_HYBRID_CODEC_V0", "1")
    text = "META:emotion=a.2345 그가 2026-04-13 리포트를 정밀하게 생성했다"
    r0 = client.post("/v1/compress", json={"text": text})
    assert r0.status_code == 200
    payload = r0.json().get("integrity_flags", {}).get("hybrid_codec_v0_payload")
    assert isinstance(payload, dict)

    r1 = client.post("/v1/expand", json={"payload": payload})
    assert r1.status_code == 200
    assert r1.json().get("text") == text


def test_hybrid_codec_v0_default_on_canary(monkeypatch):
    monkeypatch.delenv("COMPRESSION_API_USE_HYBRID_CODEC_V0", raising=False)
    monkeypatch.delenv("COMPRESSION_API_FORCE_DISABLE_HYBRID_CODEC_V0", raising=False)
    from scripts import compression_token_api_stub as stub

    stub._hybrid_codec_v0_enabled.cache_clear()
    r = client.post("/v1/compress", json={"text": "canary default on test"})
    assert r.status_code == 200
    flags = r.json().get("integrity_flags", {})
    assert flags.get("hybrid_codec_v0_enabled") is True


def test_hybrid_codec_v0_force_disable_overrides_default(monkeypatch):
    monkeypatch.delenv("COMPRESSION_API_USE_HYBRID_CODEC_V0", raising=False)
    monkeypatch.setenv("COMPRESSION_API_FORCE_DISABLE_HYBRID_CODEC_V0", "1")
    from scripts import compression_token_api_stub as stub

    stub._hybrid_codec_v0_enabled.cache_clear()
    r = client.post("/v1/compress", json={"text": "canary force off test"})
    assert r.status_code == 200
    flags = r.json().get("integrity_flags", {})
    assert flags.get("hybrid_codec_v0_enabled") in (None, False)
    assert "hybrid_codec_v0_payload" not in flags


def test_openapi_compress_examples_parity(tmp_path, monkeypatch):
    meter_path = tmp_path / "openapi_compress_meter.jsonl"
    monkeypatch.setenv("TRACK_A_METERING_LOG_PATH", str(meter_path))
    monkeypatch.setenv("COMPRESSION_API_ENTERPRISE_KEYS", "secret-enterprise-key")
    yaml = __import__("pytest").importorskip("yaml")
    spec = yaml.safe_load(OPENAPI_STUB.read_text(encoding="utf-8"))
    examples = (
        spec.get("paths", {})
        .get("/v1/compress", {})
        .get("post", {})
        .get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("examples", {})
    )
    assert {
        "mode_none",
        "mode_public_ultra_literal",
        "mode_decision_fallback",
        "mode_live",
        "mode_hydrate_with_meter_log",
    } <= set(examples.keys())

    expected_mode: dict[str, str | set[str]] = {
        "mode_none": "none",
        # public_ultra_literal depends on tier config:
        # - with enterprise key policy + missing key: ultra_literal_kpi_estimate
        # - without enterprise key policy: enterprise default, no hydration -> none
        "mode_public_ultra_literal": {"ultra_literal_kpi_estimate", "none"},
        "mode_decision_fallback": "decision_fallback",
        "mode_live": {"live", "decision_fallback"},  # live may fallback in constrained env
        "mode_hydrate_with_meter_log": "decision_fallback",
    }
    mismatches: list[dict] = []
    for key, item in examples.items():
        payload = item.get("value", {})
        if not isinstance(payload, dict) or "text" not in payload:
            continue
        headers = (
            {"x-api-key": "wrong"}
            if key == "mode_public_ultra_literal"
            else {"x-api-key": "secret-enterprise-key"}
        )
        r = client.post("/v1/compress", json=payload, headers=headers)
        if r.status_code != 200:
            mismatches.append({"example": key, "reason": "status_code", "actual_status": r.status_code})
            continue
        data = r.json()
        if data.get("api_contract_version") != "1.0.0":
            mismatches.append(
                {"example": key, "reason": "api_contract_version", "actual": data.get("api_contract_version")}
            )
        if data.get("schema_version") != "token_compression_stub_v1":
            mismatches.append({"example": key, "reason": "schema_version", "actual": data.get("schema_version")})
        if data.get("original_text") != payload["text"]:
            mismatches.append(
                {
                    "example": key,
                    "reason": "original_text",
                    "expected": payload.get("text"),
                    "actual": data.get("original_text"),
                }
            )
        mm = data.get("integrity_flags", {}).get("metrics_mode")
        exp = expected_mode.get(key)
        if isinstance(exp, set):
            if mm not in exp:
                mismatches.append({"example": key, "reason": "metrics_mode_set", "expected_any": sorted(exp), "actual": mm})
        else:
            if mm != exp:
                mismatches.append({"example": key, "reason": "metrics_mode", "expected": exp, "actual": mm})
    if mismatches:
        _write_parity_debug({"kind": "compress_examples_parity"}, mismatches)
    assert not mismatches
    assert meter_path.read_text(encoding="utf-8").strip()


def test_openapi_expand_examples_parity():
    yaml = __import__("pytest").importorskip("yaml")
    spec = yaml.safe_load(OPENAPI_STUB.read_text(encoding="utf-8"))
    examples = (
        spec.get("paths", {})
        .get("/v1/expand", {})
        .get("post", {})
        .get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("examples", {})
    )
    assert {"from_none_mode", "from_decision_fallback_mode", "from_live_mode"} <= set(examples.keys())

    mismatches: list[dict] = []
    for item in examples.values():
        payload = item.get("value", {})
        if not isinstance(payload, dict) or "payload" not in payload:
            continue
        raw = str(payload["payload"].get("original_text", ""))
        r = client.post("/v1/expand", json=payload)
        if r.status_code != 200:
            mismatches.append({"reason": "status_code", "actual_status": r.status_code, "payload": payload})
            continue
        body = r.json()
        if body.get("api_contract_version") != "1.0.0":
            mismatches.append(
                {"reason": "api_contract_version", "actual": body.get("api_contract_version"), "payload": payload}
            )
        if body.get("text") != raw:
            mismatches.append({"reason": "text", "expected": raw, "actual": body.get("text"), "payload": payload})
    if mismatches:
        _write_parity_debug({"kind": "expand_examples_parity"}, mismatches)
    assert not mismatches


def test_openapi_includes_metering_log_path():
    yaml = __import__("pytest").importorskip("yaml")
    spec = yaml.safe_load(OPENAPI_STUB.read_text(encoding="utf-8"))
    assert "/v1/metering/log" in spec.get("paths", {})


def test_openapi_v1_semantic_pointer_contract_fields() -> None:
    yaml = __import__("pytest").importorskip("yaml")
    spec = yaml.safe_load(OPENAPI_STUB.read_text(encoding="utf-8"))
    schemas = spec.get("components", {}).get("schemas", {})
    eval_ctx = schemas.get("EvalContext", {})
    compress_resp = schemas.get("CompressResponse", {})
    eval_props = eval_ctx.get("properties", {})
    resp_props = compress_resp.get("properties", {})
    assert "emit_semantic_pointer" in eval_props
    assert eval_props["emit_semantic_pointer"].get("type") == "boolean"
    assert "semantic_pointer" in resp_props
    assert resp_props["semantic_pointer"].get("type") == "object"


def test_metering_log_append(tmp_path, monkeypatch):
    log = tmp_path / "meter.jsonl"
    monkeypatch.setenv("TRACK_A_METERING_LOG_PATH", str(log))
    r = client.post(
        "/v1/metering/log",
        json={
            "sla_track": "active",
            "tokens_before": 100,
            "tokens_after": 51,
            "saving_rate": 0.49,
        },
    )
    assert r.status_code == 200
    j = r.json()
    assert j.get("accepted") is True
    assert j.get("meter_schema") == "track_a_metering_log_v1"
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["tokens_before"] == 100
    assert row["meter_schema"] == "track_a_metering_log_v1"


def test_metering_log_validation_422():
    r = client.post(
        "/v1/metering/log",
        json={"sla_track": "active", "tokens_before": -1, "tokens_after": 0},
    )
    assert r.status_code == 422


def test_compress_meter_log_appends_jsonl(tmp_path, monkeypatch):
    log = tmp_path / "meter_from_compress.jsonl"
    monkeypatch.setenv("TRACK_A_METERING_LOG_PATH", str(log))
    r = client.post(
        "/v1/compress",
        json={
            "text": "meter log test hangul 테스트",
            "client_request_id": "req-meter-compress-1",
            "eval_context": {
                "hydrate_metrics": True,
                "meter_log": True,
            },
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("integrity_flags", {}).get("meter_log_appended") is True
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row.get("client_request_id") == "req-meter-compress-1"
    assert row.get("notes") == "from_compress_eval_context_meter_log"


def test_secure_l1_side_channel_wire_endpoint_success_with_fake_provider(monkeypatch):
    from scripts import compression_token_api_stub as stub

    class _FakeProvider:
        def encrypt(self, *, key_id: str, plaintext: bytes, aad: bytes, track: str):
            _ = (key_id, aad, track)
            return (b"n" * 12, plaintext[::-1], b"t" * 16)

        def decrypt(self, *, key_id: str, nonce: bytes, ciphertext: bytes, tag: bytes, aad: bytes, track: str):
            _ = (key_id, aad, track)
            assert nonce == b"n" * 12
            assert tag == b"t" * 16
            return ciphertext[::-1]

    monkeypatch.setattr(stub, "_AesGcmCryptographyProvider", lambda: _FakeProvider())
    r = client.post(
        "/v1/research/l1_side_channel/wire/secure",
        json={
            "track": "b_track",
            "side_channel": {
                "swap_log": [[0, 1]],
                "typo_patches": [],
                "oov_stack": [],
            },
        },
    )
    assert r.status_code == 200
    d = r.json()
    assert d.get("schema") == "l1_side_channel_secure_wire_v1"
    env = d.get("envelope") or {}
    assert env.get("schema") == "mkm_secure_payload_envelope_v1"
    assert d.get("integrity_flags", {}).get("secure_envelope") is True
    assert d.get("integrity_flags", {}).get("track") == "b_track"


def test_secure_l1_side_channel_wire_endpoint_invalid_track():
    r = client.post(
        "/v1/research/l1_side_channel/wire/secure",
        json={
            "track": "wrong",
            "side_channel": {
                "swap_log": [],
                "typo_patches": [],
                "oov_stack": [],
            },
        },
    )
    assert r.status_code == 200
    d = r.json()
    assert d.get("integrity_flags", {}).get("error") == "invalid_track"


def test_secure_l1_side_channel_wire_endpoint_with_env_keys(monkeypatch):
    pytest.importorskip("cryptography")

    # 32-byte AES-256 keys (base64url) for A/B track split.
    a_key = base64.urlsafe_b64encode(b"A" * 32).decode("ascii")
    b_key = base64.urlsafe_b64encode(b"B" * 32).decode("ascii")
    monkeypatch.setenv("MKM_ENVELOPE_A_TRACK_KEY_B64", a_key)
    monkeypatch.setenv("MKM_ENVELOPE_B_TRACK_KEY_B64", b_key)
    monkeypatch.setenv("MKM_ENVELOPE_A_TRACK_KEY_ID", "kms/a-track/test-v1")
    monkeypatch.setenv("MKM_ENVELOPE_B_TRACK_KEY_ID", "kms/b-track/test-v1")

    for track, key_id in (("a_track", "kms/a-track/test-v1"), ("b_track", "kms/b-track/test-v1")):
        r = client.post(
            "/v1/research/l1_side_channel/wire/secure",
            json={
                "track": track,
                "side_channel": {
                    "swap_log": [[0, 1]],
                    "typo_patches": [],
                    "oov_stack": [],
                },
            },
        )
        assert r.status_code == 200
        d = r.json()
        flags = d.get("integrity_flags", {})
        assert flags.get("secure_envelope") is True
        assert flags.get("track") == track
        env = d.get("envelope", {})
        assert env.get("schema") == "mkm_secure_payload_envelope_v1"
        assert env.get("header", {}).get("track") == track
        assert env.get("header", {}).get("key_id") == key_id


def test_secure_l1_side_channel_wire_endpoint_rejects_unknown_key_provider(monkeypatch):
    monkeypatch.setenv("MKM_ENVELOPE_KEY_PROVIDER", "unknown_provider")
    r = client.post(
        "/v1/research/l1_side_channel/wire/secure",
        json={
            "track": "b_track",
            "side_channel": {
                "swap_log": [[0, 1]],
                "typo_patches": [],
                "oov_stack": [],
            },
        },
    )
    assert r.status_code == 200
    d = r.json()
    assert d.get("integrity_flags", {}).get("error") == "secure_envelope_encrypt_failed"


def test_secure_l1_side_channel_wire_endpoint_external_kms_adapter(monkeypatch):
    pytest.importorskip("cryptography")
    a_key = base64.urlsafe_b64encode(b"A" * 32).decode("ascii")
    b_key = base64.urlsafe_b64encode(b"B" * 32).decode("ascii")

    monkeypatch.setenv("MKM_ENVELOPE_KEY_PROVIDER", "external_kms")
    monkeypatch.setenv("MKM_ENVELOPE_EXTERNAL_KEY_CMD", "py scripts/fetch_secure_envelope_key_adapter.py")
    monkeypatch.setenv("MKM_ENVELOPE_EXTERNAL_KEY_B64_A_TRACK", a_key)
    monkeypatch.setenv("MKM_ENVELOPE_EXTERNAL_KEY_B64_B_TRACK", b_key)
    monkeypatch.setenv("MKM_ENVELOPE_A_TRACK_KEY_ID", "kms/a-track/ext-v1")
    monkeypatch.setenv("MKM_ENVELOPE_B_TRACK_KEY_ID", "kms/b-track/ext-v1")

    for track, key_id in (("a_track", "kms/a-track/ext-v1"), ("b_track", "kms/b-track/ext-v1")):
        r = client.post(
            "/v1/research/l1_side_channel/wire/secure",
            json={
                "track": track,
                "side_channel": {
                    "swap_log": [[0, 1]],
                    "typo_patches": [],
                    "oov_stack": [],
                },
            },
        )
        assert r.status_code == 200
        d = r.json()
        assert d.get("integrity_flags", {}).get("secure_envelope") is True
        env = d.get("envelope") or {}
        assert env.get("header", {}).get("track") == track
        assert env.get("header", {}).get("key_id") == key_id
