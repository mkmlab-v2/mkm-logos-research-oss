from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "run_truthfulqa_ab_sweep_v1.py"


def test_truthfulqa_sweep_plan_only_writes_plan(tmp_path: Path) -> None:
    out = tmp_path / "sweep_plan.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--baseline-url",
            "http://127.0.0.1:11434",
            "--candidate-url",
            "http://127.0.0.1:11434",
            "--baseline-model",
            "llama3.1:8b",
            "--candidate-models",
            "gemma4:e2b",
            "--temperatures",
            "0.0,0.1",
            "--mc-max-tokens",
            "8",
            "--generation-max-tokens",
            "96",
            "--prompt-profiles",
            "default,strict_fact",
            "--max-runs",
            "3",
            "--plan-only",
            "--out-json",
            str(out),
        ],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "truthfulqa_ab_sweep_v1"
    assert doc["plan_only"] is True
    assert doc["planned_count"] == 3

