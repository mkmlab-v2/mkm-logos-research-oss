"""Compression token API stub (FastAPI)."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

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


def test_compress_prefers_live_eval_when_requested():
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


def test_compress_reuses_live_eval_for_shadow_compare(monkeypatch):
    from scripts import compression_token_api_stub as stub

    calls = {"n": 0}

    def _fake_live_eval(text: str, *, bytes_in=None, token_in=None):
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


def test_expand_roundtrip_echo():
    r0 = client.post("/v1/compress", json={"text": "roundtrip"})
    p = r0.json()
    r1 = client.post("/v1/expand", json={"payload": p})
    assert r1.status_code == 200
    body = r1.json()
    assert body.get("text") == "roundtrip"
    assert body.get("api_contract_version") == "1.0.0"


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
        "mode_public_ultra_literal": "ultra_literal_kpi_estimate",
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
