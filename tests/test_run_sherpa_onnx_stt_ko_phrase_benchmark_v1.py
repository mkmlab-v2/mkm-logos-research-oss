from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_sherpa_onnx_stt_ko_phrase_benchmark_v1.py"


def test_benchmark_schema_output(tmp_path: Path) -> None:
    out = tmp_path / "bench.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode in (0, 1)
    data = json.loads((ROOT / "reports" / "sherpa_onnx_stt_ko_phrase_benchmark_v1_latest.json").read_text(encoding="utf-8"))
    assert data["schema"] == "sherpa_onnx_stt_ko_phrase_benchmark_v1"
    assert data["disclaimer"] == "research_only"
    assert data["phrase_count_target"] == 10
    assert "char_accuracy_avg" in data
    assert "char_accuracy_min" in data
    assert "char_accuracy_max" in data
    assert "char_accuracy_number_aware_avg" in data
    assert "char_error_rate_number_aware_avg" in data
