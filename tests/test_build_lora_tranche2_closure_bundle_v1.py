from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_build_lora_tranche2_closure_bundle_v1_runs() -> None:
    out = ROOT / "reports" / "tmp_lora_tranche2_closure_test.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_lora_tranche2_closure_bundle_v1.py"),
            "--out-json",
            str(out),
            "--skip-pytest",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lora_tranche2_closure_bundle_v1"
    assert doc["closure_ok"] is True
    assert doc["checks"]["tranche2_btrack_ready"] is True
