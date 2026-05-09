from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_mkm_myeongni_response_v2.py"
FIX = ROOT / "tests" / "fixtures" / "mkm_myeongni_response_v2.sample.json"


def test_validate_myeongni_response_v2_smoke():
    cp = subprocess.run(
        [sys.executable, str(SCRIPT), "--response-json", str(FIX)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    out = json.loads(cp.stdout)
    assert out["ok"] is True


def test_validate_myeongni_response_v2_rejects_bad_doc(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps(
            {
                "schema": "mkm_myeongni_response_v2",
                "track": "B",
                "core_layer": {"direction_core": 9},
                "coordinator_layer": {"failed_check_keys": []},
                "final_action": {"decision": "GO"},
                "governance": {"research_only": True},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    cp = subprocess.run(
        [sys.executable, str(SCRIPT), "--response-json", str(bad)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 1
    out = json.loads(cp.stdout)
    assert out["ok"] is False
