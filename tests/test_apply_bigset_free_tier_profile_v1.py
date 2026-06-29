"""BigSet free-tier profile apply + resolve (no network)."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPLY = ROOT / "scripts/apply_bigset_free_tier_profile_v1.py"
LIVE_CSV = ROOT / "docs/research/raw/bigset_benei_haelohim_cross_refs_tier0_v1.csv"


def test_apply_openrouter_free_profile_exit_zero(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    monkeypatch.setenv("BIGSET_LLM_PROFILE", "openrouter_free")
    env = {**os.environ, "BIGSET_LLM_PROFILE": "openrouter_free", "OPENROUTER_API_KEY": "test-key-not-real"}
    proc = subprocess.run(
        [sys.executable, str(APPLY)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    art = ROOT / "docs/final/artifacts/bigset_free_tier_profile_v1_latest.json"
    doc = json.loads(art.read_text(encoding="utf-8"))
    assert doc.get("ok") is True
    applied = doc.get("applied") or {}
    assert applied.get("profile_mode") == "openrouter_free"
    assert applied.get("SCHEMA_INFERENCE_MODEL") == "openrouter/free"
    assert applied.get("cost_tier") == "tier_0"


def test_resolve_azure_profile(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    monkeypatch.setenv("BIGSET_LLM_PROFILE", "azure_openai")
    from scripts.bigset_free_tier_profile_v1 import resolve_profile

    prof = resolve_profile()
    assert prof["profile_mode"] == "azure_openai"
    assert prof["OPENROUTER_BASE_URL"] == "https://test.openai.azure.com/openai/v1"
    assert prof["SCHEMA_INFERENCE_MODEL"] == "gpt-4o-mini"


def test_harness_read_ssot_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/invoke_mkm_harness_read_ssot_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    art = ROOT / "docs/final/artifacts/mkm_harness_read_ssot_v1_latest.json"
    doc = json.loads(art.read_text(encoding="utf-8"))
    assert doc.get("ok") is True
    assert "agent_never_reask_if_present" in doc


def test_intent_router_local_math():
    from scripts.mkm_intent_router_local_v1 import route

    r = route("창세기 1장 게마트리아 수치 계산")
    assert r["route"] == "local_math"


def test_resolve_ollama_profile(monkeypatch):
    monkeypatch.setenv("BIGSET_LLM_PROFILE", "ollama")
    monkeypatch.setenv("BIGSET_OLLAMA_MODEL", "gemma4:e2b")
    from scripts.bigset_free_tier_profile_v1 import resolve_profile

    prof = resolve_profile()
    assert prof["profile_mode"] == "ollama_local"
    assert prof["OPENROUTER_BASE_URL"].endswith("/v1")
    assert prof["SCHEMA_INFERENCE_MODEL"] == "gemma4:e2b"


def test_normalize_fills_citation_lock_from_live_csv():
    if not LIVE_CSV.is_file():
        return
    from scripts.bigset_agent_bridge_v1 import _normalize_rows, _validate_rows

    with LIVE_CSV.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return
    rows, notes = _normalize_rows(rows)
    valid, errors = _validate_rows(rows)
    if rows[0].get("source_url") and not (rows[0].get("citation_lock_anchor") or "").strip():
        assert "citation_lock_anchor_from_source_url" in notes
    assert valid, errors
