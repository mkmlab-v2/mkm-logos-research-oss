"""Phase1A integrity sub-gates."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INTEGRITY = REPO / "scripts/universal_root_gtm_integrity_lib_v1.py"


def test_integrity_passes_with_current_artifact():
    subprocess.run(
        [sys.executable, str(REPO / "scripts/run_universal_root_baseline_compare_v1.py")],
        cwd=str(REPO),
        check=True,
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "from scripts.universal_root_gtm_integrity_lib_v1 import evaluate_phase1a_integrity;"
            "import json; print(json.dumps(evaluate_phase1a_integrity()))",
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(proc.stdout.strip())
    assert doc["integrity_ok"] is True
    assert not doc["violations"]
