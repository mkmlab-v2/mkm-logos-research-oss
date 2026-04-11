"""export_general_prophecy_to_jsonl: fixture round-trip via subprocess."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "general_prophecy_registry_macro_h2_2026_pack_v1.json"
SCRIPT = ROOT / "scripts" / "export_general_prophecy_to_jsonl.py"


def test_export_macro_fixture_stdout_jsonl() -> None:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "-i", str(FIXTURE), "--stdout-only"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    lines = [json.loads(ln) for ln in r.stdout.strip().splitlines() if ln.strip()]
    assert len(lines) == 5
    for row in lines:
        assert "instruction" in row and "output" in row
        assert row["output"].startswith("[HYPO] (B-Track Research)")
