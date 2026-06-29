from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evaluate_sherpa_onnx_stt_quality_btrack_v1.py"


def test_quality_eval_schema(tmp_path: Path) -> None:
    out = tmp_path / "quality.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema"] == "sherpa_onnx_stt_quality_btrack_v1"
    assert 0.0 <= float(data["char_accuracy"]) <= 1.0
    assert data["disclaimer"] == "research_only"
