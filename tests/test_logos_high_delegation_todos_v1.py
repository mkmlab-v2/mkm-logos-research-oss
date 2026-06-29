from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run(args: list[str], timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)


def test_postit_v2_and_quality_gate_smoke() -> None:
    cp1 = _run(["scripts/build_41k_postit_shadow_v2.py", "--max-rows", "200"])
    assert cp1.returncode == 0, cp1.stderr
    cp2 = _run(["scripts/refine_31k_key_verse_shadow_v2.py", "--top-n", "64"])
    assert cp2.returncode == 0, cp2.stderr
    cp3 = _run(["scripts/validate_shadow_postits_quality_v1.py"])
    assert cp3.returncode == 0, cp3.stderr
    q = json.loads((ROOT / "reports/shadow_postits_quality_gate_v1_latest.json").read_text(encoding="utf-8-sig"))
    assert q["summary"]["overall_ok"] is True


def test_anchor_index_and_dss_plan_smoke() -> None:
    cp1 = _run(["scripts/build_logos_bidirectional_anchor_index_v1.py"])
    assert cp1.returncode == 0, cp1.stderr
    cp2 = _run(["scripts/build_dss_apocrypha_shadow_lane_pilot_plan_v1.py"])
    assert cp2.returncode == 0, cp2.stderr
    idx = json.loads((ROOT / "reports/logos_bidirectional_anchor_index_v1_latest.json").read_text(encoding="utf-8-sig"))
    assert (idx.get("summary") or {}).get("verse_nodes", 0) > 0
