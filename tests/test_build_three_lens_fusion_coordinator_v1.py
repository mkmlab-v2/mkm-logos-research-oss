from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_three_lens_fusion_coordinator_v1.py"


def test_build_three_lens_fusion_coordinator_smoke(tmp_path: Path) -> None:
    out = tmp_path / "three_lens_fusion.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--sasang-json",
            str(ROOT / "reports" / "sasang_rule_based_response_v1_latest.json"),
            "--myeongni-json",
            str(ROOT / "docs" / "final" / "artifacts" / "mkm_myeongni_response_v2_latest.json"),
            "--logos-json",
            str(ROOT / "docs" / "final" / "artifacts" / "logos_response_v1_retry_selected_latest.json"),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "three_lens_fusion_coordinator_v1"
    assert isinstance(doc["fusion"]["logos_non_gating_ok"], bool)
    assert doc["coordinator"]["research_only"] is True
    assert doc["coordinator"]["human_signoff_required"] is True
    vec = doc["fusion"]["common_feature_vector_v1"]
    assert vec["schema"] == "three_lens_common_feature_vector_v1"
    assert 0.0 <= float(vec["sasang_stress_score_0_1"]) <= 1.0
    assert 0.0 <= float(vec["myeongni_direction_score_0_1"]) <= 1.0
    assert 0.0 <= float(vec["myeongni_confidence_score_0_1"]) <= 1.0
    assert 0.0 <= float(vec["logos_tension_score_0_1"]) <= 1.0
    if vec["chronicle_signal_score_0_1"] is not None:
        assert 0.0 <= float(vec["chronicle_signal_score_0_1"]) <= 1.0
    assert isinstance(vec["chronicle_evidence_pointers"], list)


def test_build_three_lens_fusion_coordinator_field_gate_critical_override(tmp_path: Path) -> None:
    sasang_json = tmp_path / "sasang.json"
    myeongni_json = tmp_path / "myeongni.json"
    logos_json = tmp_path / "logos.json"
    field_gate_json = tmp_path / "field_gate.json"
    out = tmp_path / "three_lens_fusion.json"

    sasang_json.write_text(
        json.dumps(
            {
                "sections": {
                    "byungjeungyakri_transition": {
                        "state": "calm",
                        "next_state_probabilities": [{"state": "stress", "probability": 0.1}],
                    }
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    myeongni_json.write_text(
        json.dumps({"final_action": {"decision": "GO"}}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logos_json.write_text(
        json.dumps(
            {
                "final_insight_non_gating": "[NON_GATING] contextual only",
                "ontology_trace": {"non_gating_only": True},
                "archetypal_chaos_order_phase": {"tension_score": 0.2},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    field_gate_json.write_text(
        json.dumps({"schema": "one_plus_three_gate_decision_v1", "gate_level": "critical"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--sasang-json",
            str(sasang_json),
            "--myeongni-json",
            str(myeongni_json),
            "--logos-json",
            str(logos_json),
            "--field-gate-json",
            str(field_gate_json),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["coordinator"]["action"] == "HOLD"
    assert doc["coordinator"]["field_override"]["applied"] is True
    assert doc["coordinator"]["field_override"]["reason"] == "field_gate_critical_override"
