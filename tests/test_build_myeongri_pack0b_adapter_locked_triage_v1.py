from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_myeongri_pack0b_adapter_locked_triage_v1.py"
OUT = ROOT / "reports" / "myeongri_pack0b_adapter_locked_triage_latest.json"


def test_build_pack0b_adapter_locked_triage_smoke() -> None:
    subprocess.check_call([sys.executable, str(BUILD)], cwd=str(ROOT))
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "myeongri_pack0b_adapter_locked_triage_v1"
    assert doc["research_only"] is True
    assert isinstance(doc["runs"], list) and len(doc["runs"]) >= 1
    assert doc["dominant_failure_mode"] == "model_mode_collapse_while_golden_ok"
