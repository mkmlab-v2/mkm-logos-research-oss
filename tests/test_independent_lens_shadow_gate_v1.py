# @MKM12-METADATA
# Type: Logic
# Purpose: Regression for independent lens shadow gate v1.
# Keywords: independent_lens, shadow_mode, gate

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_RUNNER = _ROOT / "scripts" / "report_independent_lens_shadow_gate.py"
_CONTRACT = _ROOT / "docs" / "final" / "artifacts" / "INDEPENDENT_LENS_SHADOW_GATE_V1_CONTRACT.json"
_FUSION = _ROOT / "docs" / "final" / "artifacts" / "independent_lens_fusion_stub_latest.json"


def test_contract_exists() -> None:
    assert _CONTRACT.is_file()
    doc = json.loads(_CONTRACT.read_text(encoding="utf-8"))
    assert doc.get("artifact_schema") == "independent_lens_shadow_gate_v1"


def test_shadow_gate_runner(tmp_path: Path) -> None:
    out = tmp_path / "shadow_gate.json"
    hist = tmp_path / "shadow_hist.jsonl"
    cp = subprocess.run(
        [
            sys.executable,
            str(_RUNNER),
            "--fusion-input",
            str(_FUSION),
            "--history-jsonl",
            str(hist),
            "--output",
            str(out),
            "--min-weekly-cycles",
            "8",
            "--min-monthly-cycles",
            "2",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "independent_lens_shadow_gate_v1"
    assert doc.get("decision") == "KEEP_OBSERVATION_ONLY"
    assert doc.get("allow_a_track_binding") is False
    assert isinstance(doc.get("blockers"), list)


def test_shadow_gate_requires_explicit_override_flag(tmp_path: Path) -> None:
    out = tmp_path / "shadow_gate_fail.json"
    hist = tmp_path / "shadow_hist_fail.jsonl"
    cp = subprocess.run(
        [
            sys.executable,
            str(_RUNNER),
            "--fusion-input",
            str(_FUSION),
            "--history-jsonl",
            str(hist),
            "--output",
            str(out),
            "--ts-override-utc",
            "2026-03-31T23:59:59Z",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode != 0
    assert "allow-ts-override" in cp.stderr or "allow-ts-override" in cp.stdout
