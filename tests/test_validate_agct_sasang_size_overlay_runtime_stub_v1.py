from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_agct_sasang_size_overlay_runtime_stub_v1.py"
VALIDATE = ROOT / "scripts" / "validate_agct_sasang_size_overlay_runtime_stub_v1.py"


def test_validate_runtime_stub_ok(tmp_path: Path) -> None:
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
    stub = tmp_path / "runtime_stub.json"
    subprocess.check_call(
        [
            sys.executable,
            str(BUILD),
            "--overlay-candidate-json",
            str(src),
            "--runtime-enabled",
            "--output-json",
            str(stub),
        ],
        cwd=str(ROOT),
    )
    r = subprocess.run(
        [sys.executable, str(VALIDATE), "--input-json", str(stub)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
