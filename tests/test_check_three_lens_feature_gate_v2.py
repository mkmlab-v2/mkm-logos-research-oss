from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts" / "build_three_lens_fusion_coordinator_v1.py"
GATE_SCRIPT = ROOT / "scripts" / "check_three_lens_feature_gate_v2.py"


def test_check_three_lens_feature_gate_v2_smoke(tmp_path: Path) -> None:
    fusion_out = tmp_path / "three_lens_fusion.json"
    gate_out = tmp_path / "three_lens_feature_gate_v2.json"

    cp_build = subprocess.run(
        [
            sys.executable,
            str(BUILD_SCRIPT),
            "--sasang-json",
            str(ROOT / "reports" / "sasang_rule_based_response_v1_latest.json"),
            "--myeongni-json",
            str(ROOT / "docs" / "final" / "artifacts" / "mkm_myeongni_response_v2_latest.json"),
            "--logos-json",
            str(ROOT / "docs" / "final" / "artifacts" / "logos_response_v1_retry_selected_latest.json"),
            "--output-json",
            str(fusion_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp_build.returncode == 0, cp_build.stderr + cp_build.stdout

    cp_gate = subprocess.run(
        [
            sys.executable,
            str(GATE_SCRIPT),
            "--input-json",
            str(fusion_out),
            "--output-json",
            str(gate_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp_gate.returncode == 0, cp_gate.stderr + cp_gate.stdout

    doc = json.loads(gate_out.read_text(encoding="utf-8"))
    policy = json.loads((ROOT / "docs" / "final" / "artifacts" / "three_lens_staged_inclusion_policy_v1.json").read_text(encoding="utf-8-sig"))
    guardrails = policy.get("guardrails") if isinstance(policy.get("guardrails"), dict) else {}
    assert doc["schema"] == "three_lens_feature_gate_v2"
    assert doc["decision"]["action"] in {"GO", "WATCH", "HOLD"}
    assert doc["decision"]["human_signoff_required"] is bool(guardrails.get("human_signoff_required", True))
    assert doc["decision"]["research_only"] is bool(guardrails.get("research_only", True))
    assert 0.0 <= float(doc["metrics"]["risk_score_0_1"]) <= 1.0
    assert 0.0 <= float(doc["metrics"]["opportunity_score_0_1"]) <= 1.0
    assert "feature_status" in doc
    assert "chronicle_enabled_by_policy" in doc["metrics"]


def test_check_three_lens_feature_gate_v2_watch_bias_relief(tmp_path: Path) -> None:
    fusion_in = tmp_path / "fusion.json"
    gate_out = tmp_path / "gate.json"
    history_jsonl = tmp_path / "shadow.jsonl"

    fusion_doc = {
        "fusion": {
            "logos_non_gating_ok": True,
            "common_feature_vector_v1": {
                "sasang_stress_score_0_1": 0.3,
                "myeongni_direction_score_0_1": 0.46,
                "myeongni_confidence_score_0_1": 0.8,
                "logos_tension_score_0_1": 0.32,
                "chronicle_signal_score_0_1": 0.43,
                "chronicle_evidence_pointers": [
                    "docs/final/artifacts/chronicle_history_news_signal_weekly_eval_latest.json"
                ],
            },
        },
        "coordinator": {"action": "WATCH"},
    }
    fusion_in.write_text(json.dumps(fusion_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    history_jsonl.write_text("\n".join(json.dumps({"action": "WATCH"}) for _ in range(14)) + "\n", encoding="utf-8")

    cp_gate = subprocess.run(
        [
            sys.executable,
            str(GATE_SCRIPT),
            "--input-json",
            str(fusion_in),
            "--output-json",
            str(gate_out),
            "--shadow-history-jsonl",
            str(history_jsonl),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp_gate.returncode == 0, cp_gate.stderr + cp_gate.stdout
    doc = json.loads(gate_out.read_text(encoding="utf-8"))
    assert doc["decision"]["action"] == "GO"
    assert doc["decision"]["reason"] == "watch_bias_relief_low_risk_band"
    assert doc["metrics"]["watch_bias_relief_eligible"] is True


def test_check_three_lens_feature_gate_v2_stale_external_intel_guard(tmp_path: Path) -> None:
    fusion_in = tmp_path / "fusion.json"
    gate_out = tmp_path / "gate.json"
    intel_json = tmp_path / "intel.json"

    fusion_doc = {
        "fusion": {
            "logos_non_gating_ok": True,
            "common_feature_vector_v1": {
                "sasang_stress_score_0_1": 0.2,
                "myeongni_direction_score_0_1": 0.7,
                "myeongni_confidence_score_0_1": 0.9,
                "logos_tension_score_0_1": 0.2,
                "chronicle_signal_score_0_1": 0.7,
                "chronicle_evidence_pointers": [
                    "docs/final/artifacts/chronicle_history_news_signal_weekly_eval_latest.json"
                ],
            },
        },
        "coordinator": {"action": "GO"},
    }
    intel_doc = {
        "ready_for_orchestrator_context": True,
        "external_news": {"items_count": 0, "effective_items_count": 0},
    }
    fusion_in.write_text(json.dumps(fusion_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    intel_json.write_text(json.dumps(intel_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    cp_gate = subprocess.run(
        [
            sys.executable,
            str(GATE_SCRIPT),
            "--input-json",
            str(fusion_in),
            "--output-json",
            str(gate_out),
            "--external-intel-json",
            str(intel_json),
            "--require-external-intel",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp_gate.returncode == 0, cp_gate.stderr + cp_gate.stdout
    doc = json.loads(gate_out.read_text(encoding="utf-8"))
    assert doc["decision"]["action"] == "WATCH"
    assert doc["decision"]["reason"] == "stale_external_intel"
    assert doc["metrics"]["external_intel_guard_failed"] is True


def test_check_three_lens_feature_gate_v2_conditional_go_not_armed(tmp_path: Path) -> None:
    fusion_in = tmp_path / "fusion.json"
    gate_out = tmp_path / "gate.json"
    cond_policy = tmp_path / "conditional_go_policy.json"
    cond_market = tmp_path / "conditional_go_market.json"

    fusion_doc = {
        "fusion": {
            "logos_non_gating_ok": True,
            "common_feature_vector_v1": {
                "sasang_stress_score_0_1": 0.2,
                "myeongni_direction_score_0_1": 0.75,
                "myeongni_confidence_score_0_1": 0.9,
                "logos_tension_score_0_1": 0.2,
                "chronicle_signal_score_0_1": 0.72,
                "chronicle_evidence_pointers": [
                    "docs/final/artifacts/chronicle_history_news_signal_weekly_eval_latest.json"
                ],
            },
        },
        "coordinator": {"action": "GO"},
    }
    cond_policy_doc = {
        "schema": "conditional_go_policy_v1",
        "mode": "LOCKED_MODE_WITH_RECON_SLOT",
        "activation": {"min_confidence_0_1": 0.62},
        "allocation": {"recon_slot_min_pct": 0.1, "recon_slot_max_pct": 0.2},
    }
    cond_market_doc = {"activation": {"all_conditions_met": False, "confidence_0_1": 0.8}}
    fusion_in.write_text(json.dumps(fusion_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    cond_policy.write_text(json.dumps(cond_policy_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    cond_market.write_text(json.dumps(cond_market_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    cp_gate = subprocess.run(
        [
            sys.executable,
            str(GATE_SCRIPT),
            "--input-json",
            str(fusion_in),
            "--output-json",
            str(gate_out),
            "--conditional-go-policy-json",
            str(cond_policy),
            "--conditional-go-market-json",
            str(cond_market),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp_gate.returncode == 0, cp_gate.stderr + cp_gate.stdout
    doc = json.loads(gate_out.read_text(encoding="utf-8"))
    assert doc["decision"]["action"] == "WATCH"
    assert doc["decision"]["reason"] == "conditional_go_not_armed"
    assert doc["metrics"]["conditional_go_enabled"] is True
    assert doc["metrics"]["conditional_go_armed"] is False


def test_check_three_lens_feature_gate_v2_conditional_go_armed(tmp_path: Path) -> None:
    fusion_in = tmp_path / "fusion.json"
    gate_out = tmp_path / "gate.json"
    cond_policy = tmp_path / "conditional_go_policy.json"
    cond_market = tmp_path / "conditional_go_market.json"

    fusion_doc = {
        "fusion": {
            "logos_non_gating_ok": True,
            "common_feature_vector_v1": {
                "sasang_stress_score_0_1": 0.2,
                "myeongni_direction_score_0_1": 0.75,
                "myeongni_confidence_score_0_1": 0.9,
                "logos_tension_score_0_1": 0.2,
                "chronicle_signal_score_0_1": 0.72,
                "chronicle_evidence_pointers": [
                    "docs/final/artifacts/chronicle_history_news_signal_weekly_eval_latest.json"
                ],
            },
        },
        "coordinator": {"action": "GO"},
    }
    cond_policy_doc = {
        "schema": "conditional_go_policy_v1",
        "mode": "LOCKED_MODE_WITH_RECON_SLOT",
        "activation": {"min_confidence_0_1": 0.62},
        "allocation": {"recon_slot_min_pct": 0.1, "recon_slot_max_pct": 0.2},
    }
    cond_market_doc = {"activation": {"all_conditions_met": True, "confidence_0_1": 0.8}}
    fusion_in.write_text(json.dumps(fusion_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    cond_policy.write_text(json.dumps(cond_policy_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    cond_market.write_text(json.dumps(cond_market_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    cp_gate = subprocess.run(
        [
            sys.executable,
            str(GATE_SCRIPT),
            "--input-json",
            str(fusion_in),
            "--output-json",
            str(gate_out),
            "--conditional-go-policy-json",
            str(cond_policy),
            "--conditional-go-market-json",
            str(cond_market),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp_gate.returncode == 0, cp_gate.stderr + cp_gate.stdout
    doc = json.loads(gate_out.read_text(encoding="utf-8"))
    assert doc["decision"]["action"] == "GO"
    assert doc["decision"]["reason"] == "conditional_go_activation_pass"
    assert doc["metrics"]["conditional_go_enabled"] is True
    assert doc["metrics"]["conditional_go_armed"] is True
