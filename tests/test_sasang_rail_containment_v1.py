from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
GATE = _ROOT / "docs/final/artifacts/sasang_rail_containment_gate_v1_latest.json"
CHAIN = _ROOT / "reports/sasang_rail_containment_chain_v1_latest.json"
RAG = _ROOT / "docs/final/artifacts/notebooklm_lens_sasang_rag_excerpt_v1.md"


def test_containment_gate() -> None:
    if not GATE.is_file():
        pytest.skip("gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("sasang_rail_status") == "containment_ok"
    assert gate.get("send_gate") == "HOLD"


def test_rag_containment_framing() -> None:
    if not RAG.is_file():
        pytest.skip("rag excerpt missing")
    text = RAG.read_text(encoding="utf-8")
    assert "火剋金" in text
    assert "containment" in text.lower()
    assert "[HYPO]" in text


def test_containment_chain_scripts_ok() -> None:
    if not CHAIN.is_file():
        pytest.skip("chain missing")
    chain = json.loads(CHAIN.read_text(encoding="utf-8-sig"))
    step_ok = [s for s in chain.get("steps") or [] if not str(s.get("name", "")).startswith("pytest")]
    assert all(s.get("ok") for s in step_ok)
    assert chain.get("containment_gate_ok") is True
