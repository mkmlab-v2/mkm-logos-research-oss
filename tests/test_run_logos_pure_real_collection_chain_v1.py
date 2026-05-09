from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_logos_pure_real_collection_chain_v1.py"


def test_run_logos_pure_real_collection_chain_smoke(tmp_path: Path):
    out_json = tmp_path / "chain.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--output-json",
            str(out_json),
            "--max-allowed-delta",
            "0.2",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_pure_real_collection_chain_v1"
    assert len(doc.get("steps") or []) == 19

