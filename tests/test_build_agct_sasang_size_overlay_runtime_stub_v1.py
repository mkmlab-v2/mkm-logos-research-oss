from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_agct_sasang_size_overlay_runtime_stub_v1.py"


def test_build_runtime_stub_disabled_by_default(tmp_path: Path) -> None:
    src = tmp_path / "overlay_candidate.json"
    src.write_text(
        json.dumps(
            {
                "schema": "agct_sasang_size_overlay_candidate_v1",
                "gates": {"candidate_ready_for_human_review": True},
                "overlay_candidate": {
                    "low_risk_multiplier": 0.95,
                    "neutral_multiplier": 0.85,
                    "high_risk_multiplier": 0.70,
                },
                "evidence": {"best_accuracy": 0.7, "best_accuracy_permutation_p_value": 0.04, "risk_corr_pearson": 0.2},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "runtime_stub.json"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--overlay-candidate-json", str(src), "--output-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema"] == "agct_sasang_size_overlay_runtime_stub_v1"
    assert data["runtime_stub"]["enabled"] is False
    assert data["runtime_stub"]["status"] == "READY_FOR_SHADOW_DISABLED"


def test_build_runtime_stub_enabled_when_requested(tmp_path: Path) -> None:
    src = tmp_path / "overlay_candidate.json"
    src.write_text(
        json.dumps(
            {
                "schema": "agct_sasang_size_overlay_candidate_v1",
                "gates": {"candidate_ready_for_human_review": True},
                "overlay_candidate": {
                    "low_risk_multiplier": 0.95,
                    "neutral_multiplier": 0.85,
                    "high_risk_multiplier": 0.70,
                },
                "evidence": {"best_accuracy": 0.7, "best_accuracy_permutation_p_value": 0.04, "risk_corr_pearson": 0.2},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "runtime_stub.json"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--overlay-candidate-json",
            str(src),
            "--runtime-enabled",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["runtime_stub"]["enabled"] is True
    assert data["runtime_stub"]["status"] == "READY_FOR_SHADOW"
