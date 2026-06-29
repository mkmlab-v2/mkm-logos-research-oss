from __future__ import annotations

import json
from pathlib import Path

from scripts.build_compression_comparison_summary_v1 import build_summary


def test_build_compression_comparison_summary_has_schema_and_track_a() -> None:
    doc = build_summary()
    assert doc["schema"] == "comparison_summary_v1"
    ta = doc["track_a_frozen"]
    if ta.get("present"):
        assert ta["global_token_saving_rate"] is not None
    assert "guardrail" in doc


def test_build_compression_comparison_summary_writes(tmp_path: Path) -> None:
    import subprocess
    import sys

    out = tmp_path / "comparison_summary_latest.json"
    proc = subprocess.run(
        [sys.executable, "scripts/build_compression_comparison_summary_v1.py", "--out-json", str(out)],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == "comparison_summary_v1"
