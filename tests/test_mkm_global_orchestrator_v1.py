# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, doc: dict) -> None:
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")


def test_orchestrator_single_decision_smoke(tmp_path: Path) -> None:
    sasang = {
        "schema": "sasang_independent_lens_v0",
        "scores": {"direction_score": 0.2, "confidence": 0.8},
        "a_track_autobind_forbidden": False,
    }
    myeongni = {
        "schema": "mkm_myeongni_response_v2",
        "core_layer": {"direction_core": 0.3, "confidence_core": 0.8},
        "coordinator_layer": {"confidence_adjusted": 0.82},
        "final_action": {"decision": "WATCH"},
        "governance": {"research_only": False},
    }
    logos = {
        "schema": "mkm_logos_response_v2",
        "core_layer": {"direction_core": 0.25, "confidence_core": 0.9},
        "coordinator_layer": {"confidence_adjusted": 0.88},
        "final_action": {"decision": "WATCH"},
        "governance": {"research_only": False},
    }
    policy = {
        "schema": "mkm_global_orchestrator_policy_v1",
        "weights": {"sasang": 0.34, "myeongni": 0.33, "logos": 0.33},
        "decision_policy": {
            "go_confidence_cut": 0.7,
            "go_direction_abs_cut": 0.25,
            "hold_confidence_cut": 0.35,
            "hold_direction_abs_cut": 0.1,
            "fail_closed_action": "HOLD",
        },
    }
    runtime = {
        "schema": "myeongni_conflict_arbitration_runtime_mode_v1",
        "mode": "aggressive",
        "policy_hash": "abc123",
        "verification_pass": True,
    }
    realset_gate = {
        "schema": "myeongni_stage2_realset_gate_v1",
        "pass": True,
        "real_count": 60,
    }
    s = tmp_path / "s.json"
    m = tmp_path / "m.json"
    l = tmp_path / "l.json"
    p = tmp_path / "p.json"
    r = tmp_path / "runtime.json"
    g = tmp_path / "gate.json"
    out = tmp_path / "out.json"
    _write_json(s, sasang)
    _write_json(m, myeongni)
    _write_json(l, logos)
    _write_json(p, policy)
    _write_json(r, runtime)
    _write_json(g, realset_gate)

    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "mkm_global_orchestrator_v1.py"),
            "--sasang-json",
            str(s),
            "--myeongni-json",
            str(m),
            "--logos-json",
            str(l),
            "--policy-json",
            str(p),
            "--myeongni-runtime-json",
            str(r),
            "--myeongni-realset-gate-json",
            str(g),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_global_orchestrator_v1"
    assert doc["result"]["decision"] in {"GO", "WATCH", "HOLD"}
    assert doc["result"]["effective_mode"] == "aggressive"
    assert doc["result"]["policy_hash"] == "abc123"


def test_orchestrator_holds_when_realset_gate_fails(tmp_path: Path) -> None:
    sasang = {"schema": "sasang_independent_lens_v0", "scores": {"direction_score": 0.2, "confidence": 0.8}}
    myeongni = {
        "schema": "mkm_myeongni_response_v2",
        "core_layer": {"direction_core": 0.3, "confidence_core": 0.8},
        "coordinator_layer": {"confidence_adjusted": 0.82},
        "final_action": {"decision": "WATCH"},
        "governance": {"research_only": False},
    }
    logos = {
        "schema": "mkm_logos_response_v2",
        "core_layer": {"direction_core": 0.25, "confidence_core": 0.9},
        "coordinator_layer": {"confidence_adjusted": 0.88},
        "final_action": {"decision": "WATCH"},
        "governance": {"research_only": False},
    }
    policy = {
        "schema": "mkm_global_orchestrator_policy_v1",
        "weights": {"sasang": 0.34, "myeongni": 0.33, "logos": 0.33},
        "decision_policy": {"fail_closed_action": "HOLD"},
    }
    runtime = {"schema": "myeongni_conflict_arbitration_runtime_mode_v1", "mode": "aggressive", "policy_hash": "h1", "verification_pass": True}
    realset_gate = {"schema": "myeongni_stage2_realset_gate_v1", "pass": False, "real_count": 10}
    s = tmp_path / "s.json"
    m = tmp_path / "m.json"
    l = tmp_path / "l.json"
    p = tmp_path / "p.json"
    r = tmp_path / "runtime.json"
    g = tmp_path / "gate.json"
    out = tmp_path / "out.json"
    _write_json(s, sasang)
    _write_json(m, myeongni)
    _write_json(l, logos)
    _write_json(p, policy)
    _write_json(r, runtime)
    _write_json(g, realset_gate)

    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "mkm_global_orchestrator_v1.py"),
            "--sasang-json",
            str(s),
            "--myeongni-json",
            str(m),
            "--logos-json",
            str(l),
            "--policy-json",
            str(p),
            "--myeongni-runtime-json",
            str(r),
            "--myeongni-realset-gate-json",
            str(g),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 2
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["result"]["decision"] == "HOLD"
    assert doc["result"]["reason"] == "myeongni_stage2_realset_gate_fail"


def test_orchestrator_threshold_regression_watch_below_go_cut(tmp_path: Path) -> None:
    sasang = {
        "schema": "sasang_independent_lens_v0",
        "scores": {"direction_score": 0.17, "confidence": 0.7115},
        "a_track_autobind_forbidden": False,
    }
    myeongni = {
        "schema": "mkm_myeongni_response_v2",
        "core_layer": {"direction_core": 0.15663, "confidence_core": 0.488836},
        "coordinator_layer": {"confidence_adjusted": 0.53655},
        "final_action": {"decision": "WATCH"},
        "governance": {"research_only": False},
    }
    logos = {
        "schema": "mkm_logos_response_v2",
        "core_layer": {"direction_core": 0.100534, "confidence_core": 0.986114},
        "coordinator_layer": {"confidence_adjusted": 1.0},
        "final_action": {"decision": "WATCH"},
        "governance": {"research_only": False},
    }
    policy = {
        "schema": "mkm_global_orchestrator_policy_v1",
        "weights": {"sasang": 0.34, "myeongni": 0.33, "logos": 0.33},
        "decision_policy": {
            "go_confidence_cut": 0.53,
            "go_direction_abs_cut": 0.15,
            "hold_confidence_cut": 0.35,
            "hold_direction_abs_cut": 0.1,
            "fail_closed_action": "HOLD",
        },
    }
    runtime = {
        "schema": "myeongni_conflict_arbitration_runtime_mode_v1",
        "mode": "aggressive",
        "policy_hash": "reg-cut",
        "verification_pass": True,
    }
    realset_gate = {"schema": "myeongni_stage2_realset_gate_v1", "pass": True, "real_count": 60}

    s = tmp_path / "s.json"
    m = tmp_path / "m.json"
    l = tmp_path / "l.json"
    p = tmp_path / "p.json"
    r = tmp_path / "runtime.json"
    g = tmp_path / "gate.json"
    out = tmp_path / "out.json"
    _write_json(s, sasang)
    _write_json(m, myeongni)
    _write_json(l, logos)
    _write_json(p, policy)
    _write_json(r, runtime)
    _write_json(g, realset_gate)

    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "mkm_global_orchestrator_v1.py"),
            "--sasang-json",
            str(s),
            "--myeongni-json",
            str(m),
            "--logos-json",
            str(l),
            "--policy-json",
            str(p),
            "--myeongni-runtime-json",
            str(r),
            "--myeongni-realset-gate-json",
            str(g),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["result"]["decision"] == "WATCH"
    assert doc["result"]["reason"] == "intermediate_signal"


def test_orchestrator_threshold_regression_go_at_or_above_cut(tmp_path: Path) -> None:
    sasang = {
        "schema": "sasang_independent_lens_v0",
        "scores": {"direction_score": 0.17, "confidence": 0.7115},
        "a_track_autobind_forbidden": False,
    }
    myeongni = {
        "schema": "mkm_myeongni_response_v2",
        "core_layer": {"direction_core": 0.15663, "confidence_core": 0.488836},
        "coordinator_layer": {"confidence_adjusted": 0.53655},
        "final_action": {"decision": "WATCH"},
        "governance": {"research_only": False},
    }
    logos = {
        "schema": "mkm_logos_response_v2",
        "core_layer": {"direction_core": 0.100534, "confidence_core": 0.986114},
        "coordinator_layer": {"confidence_adjusted": 1.0},
        "final_action": {"decision": "WATCH"},
        "governance": {"research_only": False},
    }
    policy = {
        "schema": "mkm_global_orchestrator_policy_v1",
        "weights": {"sasang": 0.34, "myeongni": 0.33, "logos": 0.33},
        "decision_policy": {
            "go_confidence_cut": 0.53,
            "go_direction_abs_cut": 0.14,
            "hold_confidence_cut": 0.35,
            "hold_direction_abs_cut": 0.1,
            "fail_closed_action": "HOLD",
        },
    }
    runtime = {
        "schema": "myeongni_conflict_arbitration_runtime_mode_v1",
        "mode": "aggressive",
        "policy_hash": "reg-cut",
        "verification_pass": True,
    }
    realset_gate = {"schema": "myeongni_stage2_realset_gate_v1", "pass": True, "real_count": 60}

    s = tmp_path / "s.json"
    m = tmp_path / "m.json"
    l = tmp_path / "l.json"
    p = tmp_path / "p.json"
    r = tmp_path / "runtime.json"
    g = tmp_path / "gate.json"
    out = tmp_path / "out.json"
    _write_json(s, sasang)
    _write_json(m, myeongni)
    _write_json(l, logos)
    _write_json(p, policy)
    _write_json(r, runtime)
    _write_json(g, realset_gate)

    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "mkm_global_orchestrator_v1.py"),
            "--sasang-json",
            str(s),
            "--myeongni-json",
            str(m),
            "--logos-json",
            str(l),
            "--policy-json",
            str(p),
            "--myeongni-runtime-json",
            str(r),
            "--myeongni-realset-gate-json",
            str(g),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["result"]["decision"] == "GO"
    assert doc["result"]["reason"] == "high_confidence_and_direction"
