from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEEDS_OUT = ROOT / "projects/mkm/mkm-life/public/data/mkm_observation_study_profile_seeds_v1.json"
EXPORT = ROOT / "scripts/export_mkm_observation_study_profile_seeds_v1.py"


def test_export_study_profile_seeds_has_demo() -> None:
    subprocess.run([sys.executable, str(EXPORT)], cwd=ROOT, check=True)
    doc = json.loads(SEEDS_OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_observation_study_profile_seeds_v1"
    demo = next((p for p in doc["profiles"] if p.get("student_id") == "student-demo-001"), None)
    assert demo is not None
    assert demo.get("a_code_type") == "A03"
    assert demo.get("a_code_label_ko")
