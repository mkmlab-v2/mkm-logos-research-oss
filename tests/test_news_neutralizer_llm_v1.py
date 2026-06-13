from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LLM_SCRIPT = ROOT / "scripts" / "news_neutralizer_llm_v1.py"


def _load_llm_mod():
    spec = importlib.util.spec_from_file_location("news_neutralizer_llm_v1", LLM_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def llm_mod(monkeypatch: pytest.MonkeyPatch):
    for key in (
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_OPENAI_DEPLOYMENT_NAME",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GOOGLE_CLOUD_PROJECT",
        "MKM_LLM_PRIORITY",
    ):
        monkeypatch.delenv(key, raising=False)
    return _load_llm_mod()


def test_resolve_billing_explicit_azure(llm_mod, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    assert llm_mod.resolve_billing("azure") == "azure"


def test_resolve_billing_auto_prefers_azure(llm_mod, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    assert llm_mod.resolve_billing("auto") == "azure"


def test_resolve_billing_auto_developer_when_no_azure(llm_mod, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    assert llm_mod.resolve_billing("auto") == "developer"


def test_resolve_billing_invalid_raises(llm_mod) -> None:
    with pytest.raises(ValueError, match="billing must be"):
        llm_mod.resolve_billing("stripe")


def test_azure_inter_call_sleep_sec_env(llm_mod, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MKM_AZURE_LLM_INTER_CALL_SLEEP_SEC", raising=False)
    assert llm_mod.azure_inter_call_sleep_sec() == 20
    monkeypatch.setenv("MKM_AZURE_LLM_INTER_CALL_SLEEP_SEC", "5")
    assert llm_mod.azure_inter_call_sleep_sec() == 5


def test_extract_json_object_from_fence(llm_mod) -> None:
    raw = 'Here is JSON:\n```json\n{"shared_facts": ["a"], "framing_signals": []}\n```'
    obj = llm_mod.extract_json_object(raw)
    assert obj["shared_facts"] == ["a"]
