from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_layer1_layer5_integrated_gate_report_v1.py"


def test_integrated_gate_holds_on_insufficient_data(tmp_path: Path) -> None:
    l1 = tmp_path / "l1.json"
    l5 = tmp_path / "l5.json"
    out = tmp_path / "integrated.json"
    l1.write_text(json.dumps({"benchmark_status": "PASS", "metrics": {"labeled_count": 10}}), encoding="utf-8")
    l5.write_text(json.dumps({"benchmark_status": "PASS", "metrics": {"labeled_count": 10}}), encoding="utf-8")

    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--layer1-json",
            str(l1),
            "--layer5-json",
            str(l5),
            "--output-json",
            str(out),
            "--min-approved-samples",
            "50",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "layer1_layer5_integrated_gate_report_v1"
    assert doc["decision"] == "HOLD_DATA_INSUFFICIENT"
