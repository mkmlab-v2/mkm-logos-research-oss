from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "scripts" / "run_myeongni_package_b_chain_v1.py"
EXPORT = ROOT / "scripts" / "export_myeongni_package_b_baseline_v1.py"


def test_export_myeongni_package_b_baseline_v1(tmp_path: Path):
    summary = tmp_path / "summary.json"
    rec = tmp_path / "rec.json"
    out = tmp_path / "baseline.json"

    cp_chain = subprocess.run(
        [
            sys.executable,
            str(CHAIN),
            "--mode",
            "both",
            "--summary-output",
            str(summary),
            "--profile-recommendation-output",
            str(rec),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp_chain.returncode == 0, cp_chain.stderr + cp_chain.stdout

    cp_export = subprocess.run(
        [
            sys.executable,
            str(EXPORT),
            "--summary-json",
            str(summary),
            "--recommendation-json",
            str(rec),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp_export.returncode == 0, cp_export.stderr + cp_export.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_myeongni_package_b_baseline_v1"
    snap = doc["snapshot"]
    assert snap["decision_balanced"] in {"WATCH", "HOLD", "REDUCE"}
    assert snap["decision_attack"] in {"WATCH", "HOLD", "REDUCE"}
    assert snap["recommended_profile"] in {"balanced", "attack"}
