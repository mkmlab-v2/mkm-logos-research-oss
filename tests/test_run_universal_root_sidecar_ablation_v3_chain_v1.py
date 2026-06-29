"""Universal Root sidecar ablation v3 chain smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_run_universal_root_sidecar_ablation_v3_chain_v1(tmp_path: Path) -> None:
    out = tmp_path / "ablation_v3_smoke.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_universal_root_sidecar_ablation_v3_chain_v1.py"),
            "--skip-v2",
            "--skip-distortion",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "universal_root_sidecar_ablation_v3"
    assert doc["send_gate"] == "HOLD"
