from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_canon_singularity_promotion_go_no_go_v1_go(tmp_path: Path):
    promotion = tmp_path / "promotion.json"
    day7 = tmp_path / "day7.json"
    freeze_stability = tmp_path / "freeze_stability.json"
    delta_governance = tmp_path / "delta_governance.json"
    out_json = tmp_path / "go_no_go.json"
    out_md = tmp_path / "go_no_go.md"

    promotion.write_text(json.dumps({"status": "pass"}, ensure_ascii=False), encoding="utf-8")
    day7.write_text(json.dumps({"verdict": "ready"}, ensure_ascii=False), encoding="utf-8")
    freeze_stability.write_text(
        json.dumps({"status": "pass", "metrics": {"frozen_rate": 1.0}}, ensure_ascii=False),
        encoding="utf-8",
    )
    delta_governance.write_text(
        json.dumps({"status": "pass", "metrics": {"hold_streak": 3}}, ensure_ascii=False),
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_promotion_go_no_go_v1.py",
        "--promotion-gate-json",
        str(promotion),
        "--day7-checkpoint-json",
        str(day7),
        "--freeze-v2-stability-gate-json",
        str(freeze_stability),
        "--delta-governance-json",
        str(delta_governance),
        "--output-json",
        str(out_json),
        "--output-md",
        str(out_md),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["schema"] == "original_corpus_regime_singularity_canon_promotion_go_no_go_v1"
    assert data["verdict"] == "go"
    assert data["hold_reasons"] == []
    assert out_md.exists()


def test_build_canon_singularity_promotion_go_no_go_v1_no_go(tmp_path: Path):
    promotion = tmp_path / "promotion.json"
    day7 = tmp_path / "day7.json"
    freeze_stability = tmp_path / "freeze_stability.json"
    delta_governance = tmp_path / "delta_governance.json"
    out_json = tmp_path / "go_no_go.json"

    promotion.write_text(json.dumps({"status": "fail"}, ensure_ascii=False), encoding="utf-8")
    day7.write_text(json.dumps({"verdict": "hold"}, ensure_ascii=False), encoding="utf-8")
    freeze_stability.write_text(json.dumps({"status": "fail"}, ensure_ascii=False), encoding="utf-8")
    delta_governance.write_text(json.dumps({"status": "pass"}, ensure_ascii=False), encoding="utf-8")

    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_promotion_go_no_go_v1.py",
        "--promotion-gate-json",
        str(promotion),
        "--day7-checkpoint-json",
        str(day7),
        "--freeze-v2-stability-gate-json",
        str(freeze_stability),
        "--delta-governance-json",
        str(delta_governance),
        "--output-json",
        str(out_json),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["verdict"] == "no_go"
    assert "promotion_gate_ok" in data["hold_reasons"]
    assert "day7_ready_ok" in data["hold_reasons"]
    assert "freeze_v2_stability_ok" in data["hold_reasons"]

