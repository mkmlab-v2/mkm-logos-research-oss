# @MKM12-METADATA
# Type: Logic
# Purpose: B-Track hypothesis generator smoke test (stub path).
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "generate_btrack_hypothesis_prophecy_v1.py"
_BUNDLE = _ROOT / "docs" / "final" / "artifacts" / "btrack_llm_input_bundle_latest.json"


def test_generate_script_exists() -> None:
    assert _SCRIPT.is_file()


def test_stub_outputs_valid_schema(tmp_path: Path) -> None:
    if not _BUNDLE.is_file():
        import pytest

        pytest.skip("bundle not built; run build_btrack_llm_input_bundle.py first")
    out = tmp_path / "hyp.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--bundle",
            str(_BUNDLE),
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "btrack_hypothesis_prophecy_v1"
    assert doc.get("hypothesis_tier") == "B"
    assert "[HYPO]" in str(doc.get("label", ""))
    assert doc.get("prediction", {}).get("direction") in ("bull", "bear", "neutral", "abstain")


def test_validate_only_accepts_good_doc(tmp_path: Path) -> None:
    p = tmp_path / "ok.json"
    p.write_text(
        json.dumps(
            {
                "schema": "btrack_hypothesis_prophecy_v1",
                "hypothesis_tier": "B",
                "boundary_ack": True,
                "ts_utc": "2026-04-06T00:00:00Z",
                "label": "[HYPO] test",
                "prediction": {"instrument": "none", "horizon": "1d", "direction": "abstain"},
            }
        ),
        encoding="utf-8",
    )
    cp = subprocess.run(
        [sys.executable, str(_SCRIPT), "--validate-only", str(p)],
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
