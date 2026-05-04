# Keywords: meta_layer, jsonschema, agent_decisions_log, governance

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _minimal_valid_envelope() -> dict:
    return {
        "schema": "mkm_meta_layer_turn_envelope_v1",
        "turn_id": "test-turn-0001",
        "utc_timestamp": "2026-05-05T12:00:00Z",
        "risk_tier": "LOW",
        "premise_audit": {
            "question_bakes_in_answer": False,
            "hidden_premises": [],
            "fix_one_line": "State objective without presupposing solution.",
        },
        "objective_inversion": {
            "flip_sign_hypothesis": "Minimize regret instead of maximize profit.",
            "if_flipped_what_changes": "Risk sizing and evaluation horizon shift.",
        },
        "stakeholder_remap": {
            "primary_auditor": "FACT_LOCK",
            "success_criteria_for_auditor": "Cited script or artifact proves claim.",
            "failure_modes": ["Missing evidence_path", "NotebookLM-only claim"],
        },
        "contradiction_check": {
            "violates_constitution_or_gates": False,
            "hold_recommendation": "GO",
            "evidence_paths": ["scripts/verify_p0_constitution_gate_paths.ps1"],
        },
        "rival_hypotheses": {
            "H1": "Signal is noise; no edge.",
            "H2": "Signal is real but tiny; needs more data.",
            "discriminating_observation": "Holdout bucket Brier delta after N rows.",
        },
        "minimal_experiment": {
            "smallest_test": "Run pytest on one module with -q",
            "time_budget": "PT15M",
            "pass_signal": "exit 0",
            "fail_signal": "exit non-zero",
        },
        "reentry_conditions": {
            "to_execution_requires": ["jsonschema validate OK", "coherence_rules OK"],
            "blocked_until": [],
        },
        "self_refutation": {
            "what_would_falsify_my_plan": "If CI fails on main with same diff.",
            "strongest_counterargument": "Envelope overhead slows every turn.",
            "mitigation_or_accept": "Use only for HIGH+ or gated agent turns.",
        },
        "execution_barrier_labels": {
            "content_labels": ["[FACT]", "[HYPOTHESIS]"],
            "execution_allowed": True,
        },
    }


def test_example_fixture_validates():
    pytest.importorskip("jsonschema")
    from scripts.mkm_meta_layer_envelope_v1 import validate_envelope

    path = (
        ROOT
        / "docs"
        / "final"
        / "artifacts"
        / "fixtures"
        / "mkm_meta_layer_turn_envelope_v1.example.json"
    )
    assert path.is_file()
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert validate_envelope(doc) == []


def test_schema_file_exists():
    p = (
        ROOT
        / "docs"
        / "final"
        / "artifacts"
        / "schemas"
        / "mkm_meta_layer_turn_envelope_v1.schema.json"
    )
    assert p.is_file()


def test_validate_minimal_ok():
    pytest.importorskip("jsonschema")
    from scripts.mkm_meta_layer_envelope_v1 import validate_envelope

    errs = validate_envelope(_minimal_valid_envelope())
    assert errs == []


def test_coherence_h1_h2_same_fails():
    pytest.importorskip("jsonschema")
    from scripts.mkm_meta_layer_envelope_v1 import validate_envelope

    doc = _minimal_valid_envelope()
    doc["rival_hypotheses"]["H2"] = doc["rival_hypotheses"]["H1"]
    errs = validate_envelope(doc)
    assert any("H1 and H2 must differ" in e for e in errs)


def test_coherence_zero_tolerance_execution_fails():
    pytest.importorskip("jsonschema")
    from scripts.mkm_meta_layer_envelope_v1 import validate_envelope

    doc = _minimal_valid_envelope()
    doc["risk_tier"] = "ZERO_TOLERANCE"
    doc["execution_barrier_labels"]["execution_allowed"] = True
    errs = validate_envelope(doc)
    assert any("ZERO_TOLERANCE" in e for e in errs)


def test_apply_kill_switch_normalization():
    from scripts.mkm_meta_layer_envelope_v1 import apply_kill_switch_normalization

    doc = _minimal_valid_envelope()
    doc["contradiction_check"]["hold_recommendation"] = "HOLD"
    doc["execution_barrier_labels"]["execution_allowed"] = True
    out, changed = apply_kill_switch_normalization(doc)
    assert changed is True
    assert out["execution_barrier_labels"]["execution_allowed"] is False


def test_athena_validator_markdown_fence(tmp_path):
    pytest.importorskip("jsonschema")
    from scripts.mkm_meta_layer_envelope_v1 import AthenaValidator

    doc = _minimal_valid_envelope()
    md = "Preamble\n```json\n" + json.dumps(doc, ensure_ascii=False) + "\n```\n"
    v = AthenaValidator(repo_root=tmp_path / "r")
    (tmp_path / "r" / "reports").mkdir(parents=True)
    allowed, _meta, msg = v.validate_and_audit(
        md,
        mission_id="m-md",
        actor="pytest",
        append_log=True,
    )
    assert msg.startswith("[ATHENA-PASS]")
    assert allowed is True


def test_append_dry_run_writes_nothing(tmp_path):
    pytest.importorskip("jsonschema")
    from scripts.mkm_meta_layer_envelope_v1 import append_agent_decisions_log

    repo = tmp_path / "r"
    (repo / "reports").mkdir(parents=True)
    doc = _minimal_valid_envelope()
    log = append_agent_decisions_log(
        repo,
        doc,
        mission_id="m-test",
        stage="meta_layer",
        actor="pytest",
    )
    text = log.read_text(encoding="utf-8").strip()
    row = json.loads(text)
    assert row["decision"] == "meta_layer_envelope_v1"
    assert row["meta_layer_envelope"]["schema"] == "mkm_meta_layer_turn_envelope_v1"
