# @MKM12-METADATA
# Type: Logic
# Purpose: CI lock for GENERAL_PROPHECY_SCHEMA_V1.json (B / OBSERVATION_ONLY rail).
# Keywords: general_prophecy, jsonschema, constitution

"""Validate general prophecy fixture against docs/final/GENERAL_PROPHECY_SCHEMA_V1.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_PATH = _ROOT / "docs" / "final" / "GENERAL_PROPHECY_SCHEMA_V1.json"
_FIXTURE = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_sample_v1.json"
_SEED5 = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_seed_5_v1.json"
_BRIER_SMOKE = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_brier_smoke_v1.json"
_OFFICIAL_SEED = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_official_seed_v1.json"
_MACRO_H2_PACK = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_macro_h2_2026_pack_v1.json"
_PERSONALIZATION_SMOKE = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_personalization_smoke_v1.json"
_AUX_COV = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_auxiliary_covariates_brier_smoke_v1.json"
_CIV_APOC = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_civilization_apocalypse_v1.json"
_SOVEREIGN_T1_STUB = (
    _ROOT / "tests" / "fixtures" / "general_prophecy_registry_sovereign_stack_t1_stub_v1.json"
)
_CIV_APOC_T3 = _ROOT / "tests" / "fixtures" / "civilization_apocalypse_layer3_t3_pointers_v1.json"
_CIV_APOC_T3_RUBRIC = _ROOT / "tests" / "fixtures" / "civilization_apocalypse_t3_rubric_draft_v1.json"
_HIST_HOLDOUT = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_historical_holdout_v1.json"
_BIBLICAL_HISTORY_HYP = _ROOT / "docs" / "final" / "artifacts" / "biblical_history_research_hypotheses_v1.json"


@pytest.fixture(scope="module")
def _validator():
    pytest.importorskip("jsonschema")
    from jsonschema import Draft202012Validator

    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_general_prophecy_auxiliary_covariates_fixture_validates(_validator) -> None:
    assert _AUX_COV.is_file(), f"missing {_AUX_COV}"
    doc = json.loads(_AUX_COV.read_text(encoding="utf-8"))
    errs = sorted(_validator.iter_errors(doc), key=lambda e: e.path)
    assert not errs, "schema errors: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:12])
    assert len(doc.get("questions") or []) == 4


def test_general_prophecy_schema_file_exists() -> None:
    assert _SCHEMA_PATH.is_file(), f"missing {_SCHEMA_PATH}"


def test_general_prophecy_fixture_validates(_validator) -> None:
    assert _FIXTURE.is_file(), f"missing {_FIXTURE}"
    doc = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    errs = sorted(_validator.iter_errors(doc), key=lambda e: e.path)
    assert not errs, "schema errors: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:12])


def test_general_prophecy_fixture_semantics() -> None:
    doc = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    assert doc.get("schema") == "general_prophecy_registry_v1"
    assert doc.get("research_rail") == "B"
    qs = doc.get("questions")
    assert isinstance(qs, list) and len(qs) == 1
    q = qs[0]
    assert q.get("schema") == "general_prophecy_question_v1"
    assert q.get("outcome_spec", {}).get("kind") == "binary"
    assert q.get("forecasts") and q["forecasts"][0].get("source_kind") == "baseline"


def test_general_prophecy_brier_smoke_fixture_validates(_validator) -> None:
    assert _BRIER_SMOKE.is_file(), f"missing {_BRIER_SMOKE}"
    doc = json.loads(_BRIER_SMOKE.read_text(encoding="utf-8"))
    errs = sorted(_validator.iter_errors(doc), key=lambda e: e.path)
    assert not errs, "schema errors: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:12])
    qs = doc.get("questions")
    assert isinstance(qs, list) and len(qs) == 1
    assert qs[0].get("resolution", {}).get("status") == "resolved"


def test_general_prophecy_macro_h2_2026_pack_fixture_validates(_validator) -> None:
    assert _MACRO_H2_PACK.is_file(), f"missing {_MACRO_H2_PACK}"
    doc = json.loads(_MACRO_H2_PACK.read_text(encoding="utf-8"))
    errs = sorted(_validator.iter_errors(doc), key=lambda e: e.path)
    assert not errs, "schema errors: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:12])
    qs = doc.get("questions")
    assert isinstance(qs, list) and len(qs) == 5
    ids = [q.get("question_id") for q in qs]
    assert len(set(ids)) == 5


def test_general_prophecy_official_seed_fixture_validates(_validator) -> None:
    assert _OFFICIAL_SEED.is_file(), f"missing {_OFFICIAL_SEED}"
    doc = json.loads(_OFFICIAL_SEED.read_text(encoding="utf-8"))
    errs = sorted(_validator.iter_errors(doc), key=lambda e: e.path)
    assert not errs, "schema errors: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:12])
    qs = doc.get("questions")
    assert isinstance(qs, list) and len(qs) == 1
    assert qs[0].get("question_id") == "gp_2026_q3_bok_rate_cut_05p"
    assert qs[0].get("resolution", {}).get("status") == "pending"


def test_general_prophecy_seed_5_fixture_validates(_validator) -> None:
    assert _SEED5.is_file(), f"missing {_SEED5}"
    doc = json.loads(_SEED5.read_text(encoding="utf-8"))
    errs = sorted(_validator.iter_errors(doc), key=lambda e: e.path)
    assert not errs, "schema errors: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:12])
    qs = doc.get("questions")
    assert isinstance(qs, list) and len(qs) == 5
    ids = [q.get("question_id") for q in qs]
    assert len(set(ids)) == 5, "question_id values must be unique"
    for q in qs:
        assert q.get("resolution", {}).get("status") == "pending"
        assert q.get("outcome_spec", {}).get("kind") == "binary"


def test_general_prophecy_civilization_apocalypse_fixture_validates(_validator) -> None:
    assert _CIV_APOC.is_file(), f"missing {_CIV_APOC}"
    doc = json.loads(_CIV_APOC.read_text(encoding="utf-8"))
    errs = sorted(_validator.iter_errors(doc), key=lambda e: e.path)
    assert not errs, "schema errors: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:12])
    qs = doc.get("questions")
    assert isinstance(qs, list) and len(qs) == 27
    ids = [q.get("question_id") for q in qs]
    assert len(set(ids)) == 27
    sovereign = [q for q in qs if "sovereign_stack" in (q.get("domain_tags") or [])]
    assert len(sovereign) == 3
    t2_count = sum(
        1
        for q in qs
        if (q.get("forecasts") or [{}])[0].get("source_kind") == "other"
        and "t3" not in (q.get("domain_tags") or [])
    )
    assert t2_count >= 8
    t3_count = sum(1 for q in qs if "t3" in (q.get("domain_tags") or []))
    assert t3_count == 4
    assert doc.get("research_rail") == "B"
    assert doc.get("boundary_ack") is True
    for q in qs:
        assert q.get("resolution", {}).get("status") == "pending"
        assert q.get("forecasts") and q["forecasts"][0].get("brier_ready") is True
        assert q.get("epistemic_firewall")


def test_general_prophecy_sovereign_stack_t1_stub_validates(_validator) -> None:
    assert _SOVEREIGN_T1_STUB.is_file(), f"missing {_SOVEREIGN_T1_STUB}"
    doc = json.loads(_SOVEREIGN_T1_STUB.read_text(encoding="utf-8"))
    errs = sorted(_validator.iter_errors(doc), key=lambda e: e.path)
    assert not errs, "schema errors: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:12])
    qs = doc.get("questions")
    assert isinstance(qs, list) and len(qs) == 3
    ids = {q.get("question_id") for q in qs}
    assert ids == {
        "civ.gov.ondevice_did_mandate_oecd3_2035",
        "civ.tech.e2ee_default_messenger_dau_1b_2032",
        "civ.finance.self_custody_wallet_oecd5_50pct_2038",
    }
    hint = doc.get("git_commit_hint") or ""
    assert "do_not_replace_civ_apoc_fixture" in hint
    for q in qs:
        assert "sovereign_stack" in (q.get("domain_tags") or [])
        assert q.get("forecasts")[0].get("source_kind") == "baseline"
        assert q.get("outcome_spec", {}).get("kind") == "binary"


def test_general_prophecy_historical_holdout_fixture_validates(_validator) -> None:
    assert _HIST_HOLDOUT.is_file(), f"missing {_HIST_HOLDOUT}"
    doc = json.loads(_HIST_HOLDOUT.read_text(encoding="utf-8"))
    errs = sorted(_validator.iter_errors(doc), key=lambda e: e.path)
    assert not errs, "schema errors: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:12])
    qs = doc.get("questions")
    assert isinstance(qs, list) and 5 <= len(qs) <= 10
    hint = doc.get("git_commit_hint") or ""
    assert "sandbox_eval_only" in hint or "not_production" in hint
    for q in qs:
        assert q.get("question_id", "").startswith("hist.")
        assert "holdout" in (q.get("domain_tags") or [])
        res = q.get("resolution") or {}
        assert res.get("status") == "resolved"
        assert isinstance(res.get("outcome_binary"), bool)
        assert q.get("forecasts") and q["forecasts"][0].get("brier_ready") is True
        assert q.get("outcome_spec", {}).get("kind") == "binary"
        assert "NON_GATING" in (q.get("layer3_interpretation_ref") or "")


def test_biblical_history_research_hypotheses_pack_skeleton() -> None:
    assert _BIBLICAL_HISTORY_HYP.is_file(), f"missing {_BIBLICAL_HISTORY_HYP}"
    doc = json.loads(_BIBLICAL_HISTORY_HYP.read_text(encoding="utf-8"))
    assert doc.get("schema") == "biblical_history_research_hypotheses_v1"
    assert doc.get("research_rail") == "B"
    assert doc.get("hypothesis_tier") == "[HYPO]"
    assert doc.get("gating_status") == "NON_GATING"
    hyps = doc.get("hypotheses")
    assert isinstance(hyps, list) and len(hyps) == 5
    ids = {h.get("id") for h in hyps}
    assert ids == {"H-AX1", "H-BC1", "H-PL1", "H-PR1", "H-AR1"}
    for h in hyps:
        assert h.get("anchor_symbol")
        assert isinstance(h.get("keyword_groups_any"), list) and h["keyword_groups_any"]
        status = h.get("status")
        assert status == "draft_skeleton" or (
            isinstance(status, str) and status.startswith("has_chronology_sidecar")
        ), f"unexpected status for {h.get('id')}: {status}"
        if h.get("id") in {"H-AX1", "H-PL1", "H-BC1"} and status != "draft_skeleton":
            assert h.get("chronology_sidecar_ref")


def test_civilization_apocalypse_layer3_t3_pointers_fixture() -> None:
    assert _CIV_APOC_T3.is_file(), f"missing {_CIV_APOC_T3}"
    doc = json.loads(_CIV_APOC_T3.read_text(encoding="utf-8"))
    assert doc.get("schema") == "civilization_apocalypse_layer3_only_v1"
    assert doc.get("research_rail") == "B"
    assert doc.get("gating_status") == "NON_GATING"
    ptrs = doc.get("t3_pointers")
    assert isinstance(ptrs, list) and len(ptrs) == 4
    for p in ptrs:
        assert p.get("brier_ready") is True
        assert p.get("resolution_rubric") == "promoted_as_general_prophecy_question_v1_in_registry_fixture"


def test_civilization_apocalypse_t3_rubric_draft_fixture() -> None:
    assert _CIV_APOC_T3_RUBRIC.is_file(), f"missing {_CIV_APOC_T3_RUBRIC}"
    doc = json.loads(_CIV_APOC_T3_RUBRIC.read_text(encoding="utf-8"))
    assert doc.get("schema") == "civilization_apocalypse_t3_rubric_draft_v1"
    assert doc.get("research_rail") == "B"
    assert doc.get("boundary_ack") is True
    assert doc.get("hypothesis_tier") == "[HYPO]"
    assert doc.get("gating_status") == "NON_GATING"
    assert doc.get("brier_ready") is False
    assert "promoted_to_registry_fixture" in (doc.get("note") or "")
    drafts = doc.get("rubric_drafts")
    assert isinstance(drafts, list) and len(drafts) == 4
    pointer_ids = {d.get("t3_pointer_id") for d in drafts}
    assert pointer_ids == {
        "t3.greenfield_new_jerusalem",
        "t3.terminal_slo_no_tears",
        "t3.matrioshka_upload_rejected_base",
        "t3.kardashev_type1_deferred",
    }
    for entry in drafts:
        rubric = entry.get("rubric_draft")
        assert isinstance(rubric, dict)
        assert rubric.get("promotion_status") == "promoted_to_civilization_registry_fixture"
        assert rubric.get("proposed_question_id", "").startswith("civ.t3.")
        assert rubric.get("layer3_interpretation_ref") == entry.get("layer3_interpretation_ref")
        assert rubric.get("proposed_resolution_deadline_utc") == "2101-03-31T00:00:00Z"
        prob = rubric.get("draft_probability_0_1")
        assert isinstance(prob, (int, float)) and 0.0 <= prob <= 1.0


def test_general_prophecy_personalization_scope_fixture_validates(_validator) -> None:
    assert _PERSONALIZATION_SMOKE.is_file(), f"missing {_PERSONALIZATION_SMOKE}"
    doc = json.loads(_PERSONALIZATION_SMOKE.read_text(encoding="utf-8"))
    errs = sorted(_validator.iter_errors(doc), key=lambda e: e.path)
    assert not errs, "schema errors: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:12])
    q = doc["questions"][0]
    assert q.get("prophecy_track") == "personalized"
    assert q.get("personalization_scope_v1", {}).get("mode") == "cohort"
