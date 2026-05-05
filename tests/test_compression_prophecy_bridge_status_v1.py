# @MKM12-METADATA
# Type: Logic
# Purpose: Regression for compression ↔ B-track bundle bridge audit artifact.
# Keywords: compression, btrack, bridge, fact-lock

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_bridge_script_emits_schema(tmp_path: Path) -> None:
    out = tmp_path / "bridge.json"
    r = subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "build_compression_prophecy_bridge_status_v1.py"), "--output", str(out)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "compression_prophecy_bridge_status_v1"
    assert doc.get("bridge_status") in {"not_wired_v1", "wired_partial_v1"}
    assert isinstance(doc.get("wired_paths"), list)
    assert doc.get("bundle_builder_script") == "scripts/build_btrack_llm_input_bundle.py"


def test_bundle_builder_wired_to_ultra_compression_tokens() -> None:
    """Fact-Lock anchor: bundle builder now includes compression bridge context slots."""
    builder = (_ROOT / "scripts" / "build_btrack_llm_input_bundle.py").read_text(encoding="utf-8")
    assert "MULTILENS_ULTRA_COMPRESSION" in builder
    assert "ultra_compression_kpi_summary_latest.json" in builder
