from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_canon_singularity_strict_freeze_drift_gate_v1(tmp_path: Path):
    freeze = tmp_path / "freeze.json"
    health = tmp_path / "health.json"
    promo = tmp_path / "promo.json"
    bench = tmp_path / "bench.json"
    delta = tmp_path / "delta.json"
    day7 = tmp_path / "day7.json"
    out_json = tmp_path / "drift.json"
    out_md = tmp_path / "drift.md"
    hist = tmp_path / "drift_hist.jsonl"
    freeze.write_text(
        json.dumps(
            {
                "gate_status": {
                    "quality_gate_policy_status": "pass",
                    "promotion_gate_status": "pass",
                    "explainability_benchmark_status": "pass",
                    "delta_governance_status": "pass",
                    "day7_checkpoint_verdict": "hold",
                }
            }
        ),
        encoding="utf-8",
    )
    health.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
    promo.write_text(json.dumps({"status": "fail"}), encoding="utf-8")
    bench.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
    delta.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
    day7.write_text(json.dumps({"verdict": "hold"}), encoding="utf-8")
    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_strict_freeze_drift_gate_v1.py",
        "--freeze-json",
        str(freeze),
        "--quality-gate-policy-json",
        str(health),
        "--promotion-gate-json",
        str(promo),
        "--explainability-benchmark-gate-json",
        str(bench),
        "--delta-governance-json",
        str(delta),
        "--day7-checkpoint-json",
        str(day7),
        "--output-json",
        str(out_json),
        "--output-md",
        str(out_md),
        "--history-jsonl",
        str(hist),
        "--append-history",
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["status"] == "alert"
    assert data["metrics"]["drift_count"] == 1
    assert data["drifts"][0]["field"] == "promotion_gate_status"
    assert out_md.exists()
    assert hist.exists()
    assert len([x for x in hist.read_text(encoding="utf-8").splitlines() if x.strip()]) == 1


def test_build_canon_singularity_strict_freeze_drift_gate_v1_uses_vfinal_fallback(tmp_path: Path):
    vfinal = tmp_path / "vfinal.json"
    go = tmp_path / "go.json"
    health = tmp_path / "health.json"
    promo = tmp_path / "promo.json"
    bench = tmp_path / "bench.json"
    delta = tmp_path / "delta.json"
    day7 = tmp_path / "day7.json"
    stab = tmp_path / "stab.json"
    out_json = tmp_path / "drift.json"
    vfinal.write_text(
        json.dumps({"gate_status": {"promotion_go_no_go_verdict": "go", "freeze_v2_stability_status": "pass"}}),
        encoding="utf-8",
    )
    go.write_text(json.dumps({"verdict": "no_go"}), encoding="utf-8")
    health.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
    promo.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
    bench.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
    delta.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
    day7.write_text(json.dumps({"verdict": "ready"}), encoding="utf-8")
    stab.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_strict_freeze_drift_gate_v1.py",
        "--freeze-vfinal-json",
        str(vfinal),
        "--promotion-go-no-go-json",
        str(go),
        "--quality-gate-policy-json",
        str(health),
        "--promotion-gate-json",
        str(promo),
        "--explainability-benchmark-gate-json",
        str(bench),
        "--delta-governance-json",
        str(delta),
        "--day7-checkpoint-json",
        str(day7),
        "--freeze-v2-stability-gate-json",
        str(stab),
        "--output-json",
        str(out_json),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["status"] == "alert"
    assert any(d["field"] == "promotion_go_no_go_verdict" for d in data["drifts"])

