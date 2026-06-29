"""Tests for herbs/formulas alias table resolver (B-track fixture PoC)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "tests/fixtures/herbs_formulas_alias_table_minimal_v1.json"


def test_load_alias_table_fixture() -> None:
    from scripts.herbs_formulas_alias_table_v1 import load_alias_table

    doc = load_alias_table(TABLE)
    assert doc["schema"] == "herbs_formulas_alias_table_v1"
    assert doc["send_gate"] == "HOLD"
    assert len(doc["herbs"]) >= 2
    assert len(doc["formulas"]) >= 1


def test_resolve_herb_aliases() -> None:
    from scripts.herbs_formulas_alias_table_v1 import resolve_alias_queries

    doc = resolve_alias_queries(["桂枝", "계지", "Gui Zhi"], table_path=TABLE)
    assert doc["schema"] == "herbs_formulas_alias_resolve_v1"
    assert all(r["match_type"] == "herb" for r in doc["results"])
    assert doc["results"][0]["canonical_id"] == "herb:guizhi"


def test_resolve_formula_with_composition() -> None:
    from scripts.herbs_formulas_alias_table_v1 import resolve_alias_queries

    doc = resolve_alias_queries(
        ["桂枝汤", "gui zhi tang"],
        table_path=TABLE,
        include_formula_composition=True,
    )
    assert doc["results"][0]["match_type"] == "formula"
    composition = doc["results"][0]["composition"]
    assert isinstance(composition, list)
    assert len(composition) == 5
    assert composition[0]["role"] == "jun"


def test_resolve_unknown_returns_none_match() -> None:
    from scripts.herbs_formulas_alias_table_v1 import resolve_alias_queries

    doc = resolve_alias_queries(["unknown herb xyz"], table_path=TABLE)
    assert doc["results"][0]["match_type"] == "none"
    assert doc["results"][0]["confidence"] == 0.0


def test_alias_table_fixture_has_required_fields() -> None:
    doc = json.loads(TABLE.read_text(encoding="utf-8"))
    assert doc["research_only"] is True
    assert doc["expert_review_required"] is True
    for herb in doc["herbs"]:
        assert herb.get("canonical_id")
        assert herb.get("canonical_name_hans")


def test_8010_alias_resolve_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_stub import app

    monkeypatch.setenv("MKM_HERBS_FORMULAS_ALIAS_TABLE_PATH", str(TABLE))
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["herbs_formulas_alias_proxy"]["enabled"] is True

    resp = client.post(
        "/v1/research/herbs_formulas/alias-resolve",
        json={
            "queries": ["계지", "桂枝汤", "unknown-x"],
            "include_formula_composition": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["send_gate"] == "HOLD"
    assert body["expert_review_required"] is True
    assert body["results"][0]["match_type"] == "herb"
    assert body["results"][1]["match_type"] == "formula"
    assert len(body["results"][1]["composition"]) == 5
    assert body["results"][2]["match_type"] == "none"
    assert body["integrity_flags"]["alias_proxy_8010"] is True
