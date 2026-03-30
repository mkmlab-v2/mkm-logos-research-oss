from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_uplift_ab_report_generates_and_preserves_gate() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "report_gematria_4d_uplift_ab.py"
    out = root / "docs" / "final" / "artifacts" / "MULTILENS_GEMATRIA_4D_UPLIFT_AB_V1.json"
    r = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "multilens_gematria_4d_uplift_ab_v1"
    assert isinstance(doc.get("metrics_off"), dict)
    assert isinstance(doc.get("metrics_on"), dict)
    assert isinstance(doc.get("quality_gate_off"), dict)
    assert isinstance(doc.get("quality_gate_on"), dict)
    assert "jaccard_guardrail_ok" in doc.get("quality_gate_off", {})
    assert "jaccard_guardrail_ok" in doc.get("quality_gate_on", {})


def test_uplift_ab_report_accepts_custom_input_output() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "report_gematria_4d_uplift_ab.py"
    pilot = root / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_GEMATRIA_PILOT_V1.json"
    out = root / "tmp" / "MULTILENS_GEMATRIA_4D_UPLIFT_AB_PILOT_TEST.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [sys.executable, str(script), "--input", str(pilot), "--output", str(out)],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "multilens_gematria_4d_uplift_ab_v1"
    assert doc.get("source_input") == "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_GEMATRIA_PILOT_V1.json"
