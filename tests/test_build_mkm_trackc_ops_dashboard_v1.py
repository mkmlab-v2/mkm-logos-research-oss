from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_trackc_dashboard_includes_lens_music_governance_fields():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_mkm_trackc_ops_dashboard_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    p = ROOT / "docs" / "final" / "artifacts" / "mkm_trackc_ops_dashboard_latest.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    lm = (doc.get("trackc") or {}).get("lens_music_audition_governance") or {}
    assert "state" in lm
    assert "warn_ratio" in lm
    assert "warn_ratio_threshold" in lm
