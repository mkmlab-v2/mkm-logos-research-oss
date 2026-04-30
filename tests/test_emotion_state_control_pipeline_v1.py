from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_BUILD_MAPPING = ROOT / "scripts" / "build_emotion_state_mapping_v1.py"
SCRIPT_SHADOW_EVAL = ROOT / "scripts" / "run_emotion_state_shadow_eval_v1.py"
SCRIPT_PROMOTION_GATE = ROOT / "scripts" / "check_emotion_state_promotion_gate_v1.py"


def test_build_mapping_writes_three_states(tmp_path: Path) -> None:
    out = tmp_path / "emotion_mapping.json"
    proc = subprocess.run(
        [
            "py",
            str(SCRIPT_BUILD_MAPPING),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "emotion_state_mapping_v1"
    states = doc["states"]
    assert len(states) == 3
    assert [s["state"] for s in states] == ["tension", "curiosity", "calm"]
    assert all(s["safety_constraints"]["fact_check_bypass"] is False for s in states)
    assert all(s["safety_constraints"]["layer5_gate_required"] is True for s in states)


def test_shadow_eval_reports_state_metadata(tmp_path: Path) -> None:
    mapping = tmp_path / "mapping.json"
    l1 = tmp_path / "l1.json"
    l5 = tmp_path / "l5.json"
    out = tmp_path / "shadow.json"

    mapping.write_text(
        json.dumps(
            {
                "schema": "emotion_state_mapping_v1",
                "states": [
                    {
                        "state": "tension",
                        "safety_constraints": {
                            "fact_check_bypass": False,
                            "layer5_gate_required": True,
                            "hard_timeout_ms": 10000,
                        },
                    },
                    {
                        "state": "curiosity",
                        "safety_constraints": {
                            "fact_check_bypass": False,
                            "layer5_gate_required": True,
                            "hard_timeout_ms": 11000,
                        },
                    },
                    {
                        "state": "calm",
                        "safety_constraints": {
                            "fact_check_bypass": False,
                            "layer5_gate_required": True,
                            "hard_timeout_ms": 9000,
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    l1.write_text(json.dumps({"metrics": {"accuracy": 1.0}}), encoding="utf-8")
    l5.write_text(
        json.dumps({"metrics": {"recall_block": 1.0, "false_positive_rate": 0.0, "p95_gate_runtime_ms": 10.0}}),
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            "py",
            str(SCRIPT_SHADOW_EVAL),
            "--mapping-json",
            str(mapping),
            "--layer1-json",
            str(l1),
            "--layer5-json",
            str(l5),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["mapping_loaded"] is True
    assert doc["mapping_state_count"] == 3
    assert doc["mapping_state_safety_all_ok"] is True
    assert doc["mapping_states"] == ["tension", "curiosity", "calm"]


def test_promotion_gate_holds_when_state_count_below_threshold(tmp_path: Path) -> None:
    ev = tmp_path / "eval.json"
    out = tmp_path / "gate.json"
    ev.write_text(
        json.dumps(
            {
                "metrics": {
                    "stability_score": 1.0,
                    "layer5_fpr": 0.0,
                    "layer5_p95_ms": 10.0,
                },
                "mapping_loaded": True,
                "mapping_state_count": 2,
                "mapping_state_safety_all_ok": True,
            }
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            "py",
            str(SCRIPT_PROMOTION_GATE),
            "--eval-json",
            str(ev),
            "--output-json",
            str(out),
            "--min-state-count",
            "3",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["checks"]["mapping_state_count_gte_threshold"] is False
    assert doc["decision"] == "HOLD"
